"""Mordor versus Elves, with an optional native pre-positioned battalion battle."""
import json
import re
import struct


def register(smoke,mod):
    names=re.findall(r'^PlayerTemplate\s+(\w+)',(mod/'data/ini/playertemplate.ini').read_text(encoding='cp1252'),re.M)
    factions=[names.index('FactionMordor'),names.index('FactionElves')]
    original=smoke.skirmish_setup
    def factory(*args,**kwargs):
        handler=original(*args,**kwargs)
        def setup(game,tid,ctx):
            result=handler(game,tid,ctx)
            info=game.global_ptr('TheSkirmishGameInfo')
            for index,faction in enumerate(factions):
                slot=game.u32(info+smoke.SLOTS_OFF+4*index)
                if not slot:raise RuntimeError('Missing battle player slot')
                game.write(slot+smoke.SLOT_TEMPLATE,struct.pack('<i',faction))
            game.res['battle_factions']={'human':'Mordor','ai':'Elves','template_indices':factions}
            return result
        return setup
    smoke.skirmish_setup=factory


def read_battle(game):
    address=game.res.get('battle_state_address')
    if not address:return None
    return dict(zip(['stage','orcs','elves','orders','error','orcPlayer','elfPlayer','aliveOrcs','aliveElves','x','y','z'],
                    struct.unpack('<9I3f',game.read(address,48))))


def tick(game,smoke):
    frame,mode=game.logic()
    if mode!=2 or frame is None or not game.res.get('battle_state_address'):return
    state=read_battle(game)
    game.res['battle']=state
    (smoke.OUT/'battle-live.json').write_text(json.dumps(state,indent=2))
    if state['error']:return 'battle-setup-failed'
    if frame>=10 and not game.res.get('battle_spawn_requested'):
        game.arm('GameEngine::update',lambda g,t,c:{'call':g.res['battle_start_address'],'ecx':0})
        game.res['battle_spawn_requested']=frame
    elif state['stage']==2 and frame>=game.res['battle_spawn_requested']+10:
        game.arm('GameEngine::update',lambda g,t,c:{'call':g.res['battle_orders_address'],'ecx':0})
    elif state['stage']==3 and frame>=game.res.get('battle_probe_frame',0)+25:
        game.arm('GameEngine::update',lambda g,t,c:{'call':g.res['battle_probe_address'],'ecx':0})
        game.res['battle_probe_frame']=frame
    if frame>=35 and state['stage']==3 and not game.res.get('battle_screenshot'):
        game.res['battle_screenshot']=game._while_serving(lambda:smoke.capture(game.pid,smoke.OUT/'battle.png'))


def validate(output):
    report=json.loads((output/'skirmish_retail.json').read_text())
    state=report['run'].get('battle',{})
    failures=[]
    if report['outcome']!='pass':failures.append(report['outcome'])
    for key,expected in [('stage',3),('orcs',16),('elves',10),('orders',26),('error',0)]:
        if state.get(key)!=expected:failures.append(f'{key}: expected {expected}, got {state.get(key)}')
    alive=state.get('aliveOrcs',0)+state.get('aliveElves',0)
    if not 0<alive<26:failures.append('No surviving battle with confirmed battalion casualties')
    symbols=report['run'].get('strategic',{}).get('symbols',{})
    if symbols.get('betweenLogicMoves',0)<10:
        failures.append('Symbols did not move between native simulation ticks')
    result={'outcome':'fail' if failures else 'pass','failures':failures,'battle':state,
            'symbols':symbols,'first_chance':report['run'].get('first_chance'),
            'screenshot':report['run'].get('battle_screenshot')}
    (output/'battle-regression.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return 1 if failures else 0
