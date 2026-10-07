"""Native strategic/tactical transition, symbol and mouse-ray regression."""
import json
import struct
from strategic import read_state


def register(smoke):
    original=smoke.skirmish_tick

    def factory(args,samples,mode):
        args.seconds=40
        base=original(args,samples,mode)
        stage=0

        def height(game,value):
            def call(game,tid,ctx):
                view=game.u32(game.base+0x9FEA3C)
                return {'call':game.base+0x8D2B8,'ecx':view,
                        'args':[struct.unpack('<I',struct.pack('<f',value))[0]]}
            game.arm('GameEngine::update',call)

        def capture(game,name):
            shot=game._while_serving(lambda:smoke.capture(game.pid,smoke.OUT/f'strategic-{name}.png'))
            game.res.setdefault('strategic_stages',{})[name]={'state':read_state(game),'screenshot':shot}

        def tick(game):
            nonlocal stage
            result=base(game)
            frame,current_mode=game.logic()
            if current_mode!=mode or frame is None:return result
            if stage==0 and frame>=15:
                height(game,300);stage=1
            elif stage==1 and frame>=40:
                capture(game,'normal');height(game,1100);stage=2
            elif stage==2 and frame>=65:
                capture(game,'transition');height(game,2400);stage=3
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
        if not 0<transition['blend']<1:failures.append('missing intermediate transition')
        if far['projection']!=1 or far['blend']!=1:failures.append('orthographic mode not reached')
        if far['buildings']<1 or far['units']<1 or far['drawCalls']<1:failures.append('missing unit/building symbols')
        if far['lastError']:failures.append('D3D draw error')
        if restored['projection']!=0 or restored['blend']!=0:failures.append('perspective not restored')
        probe=report['run'].get('strategic_pick_probe',{})
        if probe.get('probeCalls',0)<1 or probe.get('pickPixelError',999)>1 or probe.get('parallelRayError',999)>.05:
            failures.append('orthographic native picking failed')
    result={'outcome':'fail' if failures else 'pass','failures':failures,
            'stages':stages,'pickProbe':report['run'].get('strategic_pick_probe')}
    (output/'strategic-regression.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'outcome':result['outcome'],'failures':failures},indent=2))
    return 1 if failures else 0
