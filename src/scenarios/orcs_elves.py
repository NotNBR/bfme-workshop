"""Mordor versus Elves, with an optional native pre-positioned battalion battle."""

from common.paths import ROOT
import json
import re
import struct


def register(smoke,mod,test=False):
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
            game.res['battle_verify_symbols']=test
            return result
        return setup
    smoke.skirmish_setup=factory


def read_battle(game):
    address=game.res.get('battle_state_address')
    if not address:return None
    return dict(zip(['stage','orcs','elves','orders','error','orcPlayer','elfPlayer','aliveOrcs','aliveElves','x','y','z',
                     'fogDisabled','orcBuildings','elfBuildings','completeBuildings','unitsMoved','enemyVerified',
                     'waves','reinforcementOrcs','reinforcementElves','openingCasualties','reinforcementsMoved','earlyCasualties',
                     'orcHeroes','elfHeroes','heroOrders','aliveHeroes'],
                    struct.unpack('<9I3f16I',game.read(address,112))))


def tick(game,smoke):
    frame,mode=game.logic()
    if mode!=2 or frame is None or not game.res.get('battle_state_address'):return
    state=read_battle(game)
    game.res['battle']=state
    (smoke.OUT/'battle-live.json').write_text(json.dumps(state,indent=2))
    if state['error']:return 'battle-setup-failed'
    if frame>=25 and state['stage']==3 and game.res.get('battle_verify_symbols') and not game.res.get('battle_selection_requested'):
        def select_horde(g,t,c):
            obj=g.u32(g.u32(g.base+0x9FE78C)+0xAC)
            local=g.u32(g.u32(g.base+0x9FEEE8)+0x10)
            for _ in range(20000):
                if not obj:break
                template=g.u32(obj+4);drawable=g.u32(obj+0x84);team=g.u32(obj+0x304)
                prototype=g.u32(team+0x30) if team else 0
                owner=g.u32(prototype+8) if prototype else 0
                if owner==local and drawable and template and g.read(template+0x115,1)[0]&0x20:
                    g.res['battle_selected_horde']=g.u32(obj+0x74)
                    return {'call':g.base+0x2A3805,'ecx':g.u32(g.base+0x9FEDF0),'args':[drawable]}
                obj=g.u32(obj+0x8C)
            raise RuntimeError('No local battalion found for symbol selection check')
        game.arm('GameEngine::update',select_horde)
        game.res['battle_selection_requested']=True
        return  # one native call per tick; the probe uses the same breakpoint
    if frame>=1 and not game.res.get('battle_spawn_requested'):
        game.arm('GameEngine::update',lambda g,t,c:{'call':g.res['battle_start_address'],'ecx':0})
        game.res['battle_spawn_requested']=frame
    elif state['stage']==2 and frame>=game.res['battle_spawn_requested']+10:
        game.arm('GameEngine::update',lambda g,t,c:{'call':g.res['battle_orders_address'],'ecx':0})
    elif state['stage']==3 and frame>=game.res.get('battle_probe_frame',0)+5:
        game.arm('GameEngine::update',lambda g,t,c:{'call':g.res['battle_probe_address'],'ecx':0})
        game.res['battle_probe_frame']=frame
    if frame>=35 and state['stage']==3 and not game.res.get('battle_screenshot'):
        game.res['battle_screenshot']=game._while_serving(lambda:smoke.capture(game.pid,smoke.OUT/'battle.png'))


def validate(output):
    report=json.loads((output/'skirmish_retail.json').read_text())
    state=report['run'].get('battle',{})
    failures=[]
    if report['outcome']!='pass':failures.append(report['outcome'])
    for key,expected in [('stage',3),('orcs',22),('elves',12),('orders',34),('error',0),
                         ('fogDisabled',1),('orcBuildings',8),('elfBuildings',8),
                         ('completeBuildings',16),('enemyVerified',1),('waves',4),
                         ('reinforcementOrcs',10),('reinforcementElves',4),
                         ('orcHeroes',2),('elfHeroes',2),('heroOrders',4)]:
        if state.get(key)!=expected:failures.append(f'{key}: expected {expected}, got {state.get(key)}')
    alive=state.get('aliveOrcs',0)+state.get('aliveElves',0)
    if not 0<alive<=34:failures.append('No surviving armies')
    if state.get('earlyCasualties',0)<1:failures.append('Opening armies did not fight before reinforcements')
    if state.get('reinforcementsMoved',0)<8:failures.append('Reserves did not march in from their bases')
    symbols=report['run'].get('strategic',{}).get('symbols',{})
    if symbols.get('betweenLogicMoves',0)<10:
        failures.append('Symbols did not move between native simulation ticks')
    if symbols.get('peakSelectedIcons',0)<10:
        failures.append('Selected battalion members were not highlighted')
    if symbols.get('peakEnemyIcons',0)<10:
        failures.append('Enemy symbols were not colored red')
    types=report['run'].get('strategic',{}).get('peakSymbolTypes',{})
    for kind,minimum in [('building',16),('infantry',20),('archer',20),('pike',20),('hero',4)]:
        if types.get(kind,0)<minimum:failures.append(f'Missing tactical symbols for {kind}')
    result={'outcome':'fail' if failures else 'pass','failures':failures,'battle':state,
            'symbols':symbols,'peakSymbolTypes':types,'first_chance':report['run'].get('first_chance'),
            'screenshot':report['run'].get('battle_screenshot')}
    (output/'battle-regression.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return 1 if failures else 0
