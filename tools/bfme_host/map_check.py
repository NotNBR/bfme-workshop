"""Native camera tour and render-target snapshots for the large map."""
import ctypes
import json
from pathlib import Path
import struct

from PIL import Image,ImageStat

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/ithilien-frontier'


def register(smoke):
    original=smoke.skirmish_tick
    # World positions in the authored 840 x 953 map; heights remain native units.
    shots=[('ruined-settlement',2100,2500,850),('river-ford',4200,4080,1000),
           ('north-woods',5500,6900,1100),('strategic-overview',4200,4765,15500)]
    def factory(args,samples,mode):
        args.seconds=65
        basic=original(args,samples,mode)
        stage=0;pending=None;next_frame=5
        def tick(game):
            nonlocal stage,pending,next_frame
            result=basic(game)
            frame,current=game.logic()
            if current!=mode or frame is None:return result
            if pending:
                state=struct.unpack('<6I',game.read(game.res['capture_address'],24))
                request,status,w,h,pitch,pixels=state
                if not request:
                    if status or not pixels:raise RuntimeError(f'Native screenshot failed: {status:#x}')
                    raw=game.read(pixels,pitch*h)
                    picture=Image.frombytes('RGB',(w,h),raw,'raw','BGRX',pitch,1)
                    destination=OUT/(pending+'.png');picture.save(destination)
                    deviation=sum(ImageStat.Stat(picture).stddev)/3
                    game.res.setdefault('map_shots',[]).append(dict(name=pending,path=str(destination),stddev=deviation,frame=frame))
                    pending=None;stage+=1;next_frame=frame+4
            if stage<len(shots) and frame>=next_frame and not pending:
                name,x,y,height=shots[stage]
                if game.res.get('map_shot_position')!=name:
                    def move(g,tid,ctx):
                        mem=g.k.VirtualAllocEx(ctypes.c_void_p(g.hproc),None,12,0x3000,4)
                        if not mem or not g.write(mem,struct.pack('<3f',x,y,80)):raise RuntimeError('Cannot position map camera')
                        view=g.u32(g.base+0x9FEA3C)
                        player=g.u32(g.u32(g.base+0x9FEEE8)+0x10)
                        return {'calls':[{'call':g.base+0x739790,'ecx':g.u32(g.base+0x9FE74C),'args':[g.u32(player+0x54)]},
                                         {'call':g.base+0x8D55D,'ecx':view,'args':[mem]},
                                         {'call':g.base+0x8D2B8,'ecx':view,'args':[struct.unpack('<I',struct.pack('<f',height))[0]]}]}
                    game.arm('GameEngine::update',move)
                    game.res['map_shot_position']=name;next_frame=frame+22
                else:
                    if not game.res.get('capture_address'):raise RuntimeError('Rebuild strategic DLL to enable map readback')
                    game.write(game.res['capture_address'],struct.pack('<I',1));pending=name
            return result
        return tick
    smoke.skirmish_tick=factory


def validate(output):
    report=json.loads((output/'skirmish_retail.json').read_text())
    shots=report['run'].get('map_shots',[])
    # GDI's screenshot can be blank for this D3D9 window; use the actual render target.
    errors=[]
    if report['outcome'] not in ('pass','blank-window'):errors.append(report['outcome'])
    if len(shots)!=4 or any(s['stddev']<5 for s in shots):errors.append('Missing or blank native render-target views')
    if report['run'].get('strategic',{}).get('faults',1):errors.append('Native extension fault')
    if not any(frame and frame>=100 and mode==2 for _,frame,mode in report['samples']):errors.append('Insufficient skirmish frames')
    if report.get('profile_touched'):errors.append('Original profile changed')
    result=dict(outcome='pass' if not errors else 'fail',errors=errors,shots=shots,
                game_outcome=report['outcome'],map=report['args'])
    (OUT/'native-validation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    return 1 if errors else 0
