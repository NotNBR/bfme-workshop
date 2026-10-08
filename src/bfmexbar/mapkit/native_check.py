"""Native camera tour and render-target snapshots for the large map."""

from bfmexbar.paths import ROOT
import json
from pathlib import Path
import struct

from PIL import Image,ImageStat

OUT=ROOT/'artifacts/ithilien-frontier'


def register(smoke,tour=None):
    global OUT
    map_hash=None;required_players=None;bridge_probes=[]
    original=smoke.skirmish_tick
    # World positions in the authored 840 x 953 map; heights remain native units.
    shots=[('ruined-settlement',1050,4700,1600),('wooded-hills',3500,6750,1800),
           ('mountain-pass',3550,8250,2300),('strategic-overview',4200,4765,15500)]
    if tour:
        config=json.loads(tour.read_text())
        map_hash=config.get('map_sha256')
        required_players=config.get('required_players')
        bridge_probes=config.get('bridge_probes',[])
        OUT=ROOT/config['output']
        shots=config['shots']
        if len(shots)!=4:raise ValueError('Native validation requires four distinct camera shots')
    OUT.mkdir(parents=True,exist_ok=True)
    def factory(args,samples,mode):
        args.seconds=85 if bridge_probes else 65
        basic=original(args,samples,mode)
        stage=0;pending=None;next_frame=5
        def tick(game):
            nonlocal stage,pending,next_frame
            if map_hash:game.res['authored_map_sha256']=map_hash
            result=basic(game)
            frame,current=game.logic()
            if current!=mode or frame is None:return result
            if required_players and frame>=10 and not game.res.get('player_census'):
                from bfmexbar.scenarios.eight_player import census
                game.res['player_census']=census(game)
                game.res['required_players']=required_players
            if pending:
                state=struct.unpack('<6I',game.read(game.res['capture_address'],24))
                request,status,w,h,pitch,pixels=state
                if not request:
                    if status or not pixels:raise RuntimeError(f'Native screenshot failed: {status:#x}')
                    raw=game.read(pixels,pitch*h)
                    picture=Image.frombytes('RGB',(w,h),raw,'raw','BGRX',pitch,1)
                    destination=OUT/(pending+'.png');picture.save(destination)
                    deviation=sum(ImageStat.Stat(picture).stddev)/3
                    view=game.u32(game.base+0x9FEA3C)
                    focus=struct.unpack('<3f',game.read(view+0xC,12))
                    game.res.setdefault('map_shots',[]).append(dict(name=pending,path=str(destination),stddev=deviation,frame=frame,focus=focus))
                    pending=None;stage+=1;next_frame=frame+4
            if stage<len(shots) and frame>=next_frame and not pending:
                name,x,y,height=shots[stage]
                if game.res.get('map_shot_position')!=name:
                    def move(g,tid,ctx):
                        player=g.u32(g.u32(g.base+0x9FEEE8)+0x10)
                        g.write(g.res['photo_address'],struct.pack('<I8f',2,x,y,0,0,height,0,0,0))
                        return {'call':g.base+0x739790,'ecx':g.u32(g.base+0x9FE74C),'args':[g.u32(player+0x54)]}
                    game.arm('GameEngine::update',move)
                    game.res['map_shot_position']=name;next_frame=frame+22
                else:
                    if not game.res.get('capture_address'):raise RuntimeError('Rebuild strategic DLL to enable map readback')
                    game.write(game.res['capture_address'],struct.pack('<I',1));pending=name
            if stage==len(shots) and bridge_probes:
                import bfmexbar.mapkit.bridge_check as bridge_check
                if not game.res.get('bridge_probes_requested'):
                    game.res['bridge_probes_requested']=frame
                    game.arm('GameEngine::update',lambda g,tid,ctx:bridge_check.begin(g,bridge_probes))
                elif frame>=game.res.get('bridge_probe_sample_frame',0)+5:
                    bridge_check.sample(game,frame)
                    game.res['bridge_probe_sample_frame']=frame
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
    census=report['run'].get('player_census') or {}
    required=report['run'].get('required_players')
    if required and len(census.get('builder_owners',{}))!=required:
        errors.append('Missing instantiated player builders')
    probes=report['run'].get('bridge_probes',[])
    if report['run'].get('bridge_probes_requested') and (not probes or any(not p['reached'] for p in probes)):
        errors.append('A native builder did not complete its bridge crossing')
    result=dict(outcome='pass' if not errors else 'fail',errors=errors,shots=shots,
                game_outcome=report['outcome'],map=report['args'],authored_map_sha256=report['run'].get('authored_map_sha256'),
                player_census=census,player_slots=report['run'].get('eight_player_slots'),bridge_probes=probes)
    (OUT/'native-validation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    return 1 if errors else 0
