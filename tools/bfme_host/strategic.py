"""Load the native strategic-view extension on BFME's main thread."""
import ctypes
import json
from pathlib import Path
import struct

STATE_FIELDS=['version','installed','faults','cameraCalls','drawCalls','icons','buildings','units',
              'hiddenSkipped','projection','transitions','pickCalls','height','blend','halfWidth','halfHeight','lastError',
              'probeCalls','pickPixelError','parallelRayError']


def read_state(game):
    address=game.res.get('strategic_state_address')
    if not address:return None
    data=game.read(address,80)
    if not data or len(data)!=80:return None
    return dict(zip(STATE_FIELDS,struct.unpack('<12I4f2I2f',data)))


def register(smoke, dll):
    import pefile
    dll=Path(dll).resolve()
    pe=pefile.PE(str(dll))
    state_rva=next(e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name==b'bfxState')
    probe_rva=next(e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name==b'bfxProbe')
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
                game.res['strategic_initial']=read_state(game)
                if not game.res['strategic_initial']['installed']:
                    raise RuntimeError('Strategic extension hooks were not installed')
            return {'call':load_library,'ecx':0,'args':[memory],'done':loaded}

        def run(self,timeout,tick=None,tick_every=1.0):
            def observe(game):
                state=read_state(game)
                if state:
                    self.res['strategic']=state
                    (smoke.OUT/'strategic-live.json').write_text(json.dumps(state,indent=2))
                    if state['faults']:return 'strategic-extension-fault'
                return tick(game) if tick else None
            return super().run(timeout,observe,tick_every)

    smoke.Game=StrategicGame
