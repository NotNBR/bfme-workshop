"""Native strategic/tactical transition, symbol and mouse-ray regression."""

from bfmexbar.paths import ROOT
import json
import struct
from bfmexbar.strategic.inject import read_state


def register(smoke):
    original=smoke.skirmish_tick

    def factory(args,samples,mode):
        args.seconds=40
        base=original(args,samples,mode)
        stage=0
        selected=False

        def height(game,value):
            def call(game,tid,ctx):
                view=game.u32(game.base+0x9FEA3C)
                return {'call':game.base+0x8D2B8,'ecx':view,
                        'args':[struct.unpack('<I',struct.pack('<f',value))[0]]}
            game.arm('GameEngine::update',call)

        def capture(game,name):
            shot=game._while_serving(lambda:smoke.capture(game.pid,smoke.OUT/f'strategic-{name}.png'))
            game.res.setdefault('strategic_stages',{})[name]={'state':read_state(game),'screenshot':shot}
            drawable=game.res.get('strategic_selected_drawable')
            if drawable:
                rect=struct.unpack('<4i',game.read(drawable+0x460,16))
                game.res['strategic_stages'][name]['selected_bar_width']=rect[2]-rect[0]

        def select_fortress(game,tid,ctx):
            view=game.u32(game.base+0x9FEA3C)
            x,y,_=struct.unpack('<3f',game.read(view+0xC,12))
            logic=game.u32(game.base+0x9FE78C)
            local=game.u32(game.u32(game.base+0x9FEEE8)+0x10)
            obj=game.u32(logic+0xAC)
            candidates=[]
            for _ in range(20000):
                if not obj:break
                template=game.u32(obj+4);drawable=game.u32(obj+0x84)
                team=game.u32(obj+0x304)
                prototype=game.u32(team+0x30) if team else 0
                owner=game.u32(prototype+8) if prototype else 0
                hidden=game.read(drawable+0x43D,4) if drawable else b'\1'
                if owner==local and template and drawable and not hidden[0] and game.read(template+0x108,1)[0]&0x80:
                    px,py,_=struct.unpack('<3f',game.read(obj+0x38,12))
                    distance=(px-x)**2+(py-y)**2
                    if distance<500**2:candidates.append((distance,drawable))
                obj=game.u32(obj+0x8C)
            if not candidates:raise RuntimeError('No starting structure found for health-bar regression')
            drawable=min(candidates)[1]
            game.res['strategic_selected_drawable']=drawable
            return {'call':game.base+0x2A3805,'ecx':game.u32(game.base+0x9FEDF0),'args':[drawable]}

        def tick(game):
            nonlocal stage,selected
            result=base(game)
            frame,current_mode=game.logic()
            if current_mode!=mode or frame is None:return result
            # Scenario staging may already have queued a call at this breakpoint.
            # Re-arming it would save INT3 as the original instruction byte.
            if game.va('GameEngine::update') in game.bps:return result
            if frame>=20 and not selected:
                game.arm('GameEngine::update',select_fortress);selected=True;return result
            if stage==0 and frame>=15:
                height(game,300);stage=1
            elif stage==1 and frame>=40:
                capture(game,'normal');height(game,1800);stage=2
            elif stage==2 and frame>=65:
                capture(game,'transition');height(game,4800);stage=3
            elif stage==3 and frame>=90:
                capture(game,'map')
                game.arm('GameEngine::update',lambda g,t,c:{'call':g.res['strategic_probe_address'],'ecx':0})
                stage=4
            elif stage==4 and frame>=105:
                game.res['strategic_pick_probe']=read_state(game)
                height(game,300);stage=5
            elif stage==5 and frame>=130:
                capture(game,'restored');stage=6
            return result
        return tick
    smoke.skirmish_tick=factory


def validate(output):
    report=json.loads((output/'skirmish_retail.json').read_text())
    stages=report['run'].get('strategic_stages',{})
    failures=[]
    if report['outcome']!='pass':failures.append(report['outcome'])
    for name in ('normal','transition','map','restored'):
        if name not in stages:failures.append('missing '+name)
        elif stages[name]['state']['faults']:failures.append('native fault in '+name)
    if not failures:
        normal,transition,far,restored=[stages[n]['state'] for n in ('normal','transition','map','restored')]
        if normal['projection']!=0 or normal['blend']!=0:failures.append('normal perspective not preserved')
        if normal['icons'] or restored['icons']:failures.append('symbols visible at close zoom')
        if not 0<transition['blend']<1:failures.append('missing intermediate transition')
        if transition['projection']!=0 or not .35<transition['blend']<.8:
            failures.append('expanded tilt transition did not remain angled at height 1800')
        if far['projection']!=1 or far['blend']!=1:failures.append('orthographic mode not reached')
        if far['buildings']<1 or far['units']<1 or far['drawCalls']<1:failures.append('missing unit/building symbols')
        if far['lastError']:failures.append('D3D draw error')
        if far.get('frameUpdates',0)<100 or not 0<far.get('maxBlendStep',1)<.3:
            failures.append('per-frame easing not observed')
        if not 0<stages['map'].get('selected_bar_width',0)<=36:
            failures.append('selected structure health bar is not compact')
        if stages['normal'].get('selected_bar_width',0)<=stages['map'].get('selected_bar_width',0):
            failures.append('health bar did not shrink with distance')
        if stages['normal'].get('selected_bar_width',0)>240:
            failures.append('close-up health bar is oversized')
        if restored['projection']!=0 or restored['blend']!=0:failures.append('perspective not restored')
        probe=report['run'].get('strategic_pick_probe',{})
        if probe.get('probeCalls',0)<1 or probe.get('pickPixelError',999)>1 or probe.get('parallelRayError',999)>.05:
            failures.append('orthographic native picking failed')
    from bfmexbar.strategic.trace import load
    _,trace=load(output/'camera-trace.csv')
    if trace['rendered_frames']<100:failures.append('insufficient rendered camera trace')
    if trace['maximum_pivot_error_world_units']>.05:failures.append('camera aim-point drift')
    if trace['minimum_camera_height_above_focus']<=0:failures.append('camera crossed below its focus plane')
    if report['run'].get('camera_trace_dropped',0):failures.append('camera trace overflow')
    result={'outcome':'fail' if failures else 'pass','failures':failures,
            'stages':stages,'pickProbe':report['run'].get('strategic_pick_probe'),'cameraTrace':trace}
    (output/'strategic-regression.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'outcome':result['outcome'],'failures':failures},indent=2))
    return 1 if failures else 0
