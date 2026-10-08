"""Load the native strategic-view extension on BFME's main thread."""

from bfmexbar.paths import ROOT
import ctypes
import csv
from contextlib import nullcontext
import json
from pathlib import Path
import struct

STATE_FIELDS=['version','installed','faults','cameraCalls','drawCalls','icons','buildings','units',
              'hiddenSkipped','projection','transitions','pickCalls','height','blend','halfWidth','halfHeight','lastError',
              'probeCalls','pickPixelError','parallelRayError',
              'frameUpdates','healthCalls','renderHeight','maxBlendStep','nativeBarWidth','scaledBarWidth']
TRACE_FIELDS=['sequence','phase','frame','projection','seconds','target_height','current_height',
              'terrain_height','zoom','blend','filtered_height','focus_x','focus_y','focus_z',
              'camera_x','camera_y','camera_z','back_x','back_y','back_z','elevation_degrees',
              'plane_left','plane_bottom','plane_right','plane_top','near_clip','far_clip',
              'native_bar_width','scaled_bar_width']
TRACE_SAMPLE=struct.Struct('<4I25f')


def drain_trace(game,writer):
    address=game.res.get('strategic_trace_address')
    if not address:return
    count=game.u32(address)
    previous=game.res.get('camera_trace_samples',0)
    first=max(previous+1,count-4095)
    if first>previous+1:
        game.res['camera_trace_dropped']=game.res.get('camera_trace_dropped',0)+first-previous-1
    data=game.read(address+4,4096*TRACE_SAMPLE.size)
    if not data:return
    for sequence in range(first,count+1):
        values=TRACE_SAMPLE.unpack_from(data,((sequence-1)%4096)*TRACE_SAMPLE.size)
        if values[0]!=sequence:break  # do not emit a partially written/overwritten row
        writer.writerow(values)
        game.res['camera_trace_samples']=sequence


def read_state(game):
    address=game.res.get('strategic_state_address')
    if not address:return None
    data=game.read(address,104)
    if not data or len(data)!=104:return None
    return dict(zip(STATE_FIELDS,struct.unpack('<12I4f2I2f2I4f',data)))


def register(smoke, dll, trace=False, battle=False, showcase=False):
    import pefile
    dll=Path(dll).resolve()
    pe=pefile.PE(str(dll))
    state_rva=next(e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name==b'bfxState')
    probe_rva=next(e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name==b'bfxProbe')
    trace_rva=next(e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name==b'bfxTrace')
    symbols_rva=next(e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name==b'bfxSymbols')
    reserves_rva=next(e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name==b'bfxReserveDebug')
    pips_rva=next(e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name==b'bfxPipScale')
    showcase_rva=next(e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name==b'bfxShowcase')
    capture_rva=next((e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name==b'bfxCapture'),None)
    photo_rva=next((e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name==b'bfxPhoto'),None)
    types_rva=next(e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name==b'bfxSymbolTypes')
    battle_exports={key:next(e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name==name)
                    for key,name in [('state',b'bfxBattleState'),('start',b'bfxStartBattle'),
                                     ('orders',b'bfxBattleOrders'),('probe',b'bfxBattleProbe')]}
    pe.close()
    original=smoke.Game
    smoke.RVA['bfmeXbarStrategicLoad']=0x225DA9

    class StrategicGame(original):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self.on('bfmeXbarStrategicLoad',self.load_extension)

        @staticmethod
        def load_extension(game,tid,ctx):
            path=str(dll).encode('mbcs')+b'\0'
            memory=game.k.VirtualAllocEx(ctypes.c_void_p(game.hproc),None,len(path),0x3000,4)
            if not memory or not game.write(memory,path):
                raise RuntimeError('Cannot pass the strategic extension path to BFME2')
            load_library=game.u32(game.base+0x7BA1F4)
            def loaded(game,results):
                module=results[0]
                if not module:raise RuntimeError('BFME2 could not load the strategic extension')
                game.res['strategic_state_address']=module+state_rva
                game.res['strategic_probe_address']=module+probe_rva
                game.res['strategic_trace_address']=module+trace_rva
                game.res['symbol_state_address']=module+symbols_rva
                game.res['reserve_debug_address']=module+reserves_rva
                game.res['symbol_types_address']=module+types_rva
                game.res['pip_scale_address']=module+pips_rva
                if capture_rva is not None:game.res['capture_address']=module+capture_rva
                if photo_rva is not None:game.res['photo_address']=module+photo_rva
                if showcase:
                    game.res['showcase_address']=module+showcase_rva
                    game.write(module+showcase_rva,struct.pack('<I',1))
                for key,rva in battle_exports.items():game.res['battle_'+key+'_address']=module+rva
                game.res['strategic_initial']=read_state(game)
                if not game.res['strategic_initial']['installed']:
                    raise RuntimeError('Strategic extension hooks were not installed')
            return {'call':load_library,'ecx':0,'args':[memory],'done':loaded}

        def run(self,timeout,tick=None,tick_every=1.0):
            def observe(game):
                state=read_state(game)
                if state:
                    state['veterancyPips']=dict(zip(['calls','nativeZoom','correctedZoom'],struct.unpack('<I2f',game.read(game.res['pip_scale_address'],12))))
                    state['reserveDebug']=list(struct.unpack('<6I',game.read(game.res['reserve_debug_address'],24)))
                    types=struct.unpack('<20I',game.read(game.res['symbol_types_address'],80))
                    names=['building','infantry','archer','pike','cavalry','siege','monster','hero','builder','air']
                    state['symbolTypes']=dict(zip(names,types[:10]))
                    state['peakSymbolTypes']=dict(zip(names,types[10:]))
                    symbols=game.read(game.res['symbol_state_address'],32)
                    if symbols and len(symbols)==32:
                        state['symbols']=dict(zip(['samples','interpolatedPositions','betweenLogicMoves','logicMoves',
                                                  'selectedIcons','enemyIcons','peakSelectedIcons','peakEnemyIcons'],
                                                  struct.unpack('<8I',symbols)))
                    self.res['strategic']=state
                    (smoke.OUT/'strategic-live.json').write_text(json.dumps(state,indent=2))
                    if writer:
                        drain_trace(game,writer)
                        trace_file.flush()
                    if state['faults']:return 'strategic-extension-fault'
                if battle:
                    import bfmexbar.scenarios.orcs_elves as preset
                    stopped=preset.tick(game,smoke)
                    if stopped:return stopped
                if showcase:
                    import bfmexbar.capture.showcase as recording
                    recording.observe(game,smoke)
                return tick(game) if tick else None
            trace_path=smoke.OUT/'camera-trace.csv'
            if trace:self.res['camera_trace_path']=str(trace_path)
            with (trace_path.open('w',newline='') if trace else nullcontext()) as trace_file:
                writer=csv.writer(trace_file) if trace_file else None
                if writer:writer.writerow(TRACE_FIELDS)
                return super().run(timeout,observe,tick_every)

    smoke.Game=StrategicGame
