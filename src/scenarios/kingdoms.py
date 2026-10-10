"""Native 4v4 scenario staging. Recording is an optional adapter."""
from common.paths import ROOT
from scenarios.placement import plan, FACTIONS
import json
import re
import struct
OUT=ROOT/'local/artifacts/eight-kingdoms/trailer'
VALIDATION_OUT=OUT

STATE_FIELDS=['stage','error','count','spawned','orders','alive','moved','casualties','members','initialMembers','enemyPairs']


def register(smoke,mod,record=False):
    import pefile
    config=plan(mod, output=OUT)
    names=re.findall(r'^PlayerTemplate\s+(\w+)',(mod/'data/ini/playertemplate.ini').read_text(encoding='cp1252'),re.M)
    old_setup=smoke.skirmish_setup
    def factory(*args,**kwargs):
        original=old_setup(*args,**kwargs)
        def setup(g,tid,ctx):
            result=original(g,tid,ctx);info=g.global_ptr('TheSkirmishGameInfo')
            for i,name in enumerate(FACTIONS):
                slot=g.u32(info+smoke.SLOTS_OFF+4*i)
                g.write(slot+smoke.SLOT_TEMPLATE,struct.pack('<i',names.index('Faction'+name)))
                g.write(slot+0x1c,struct.pack('<i',0 if i<4 else 1))
                g.write(slot+0x10,struct.pack('<i',i))
                g.res['eight_player_slots'][i].update(faction=name,team=1 if i<4 else 2,start=i+1,template=names.index('Faction'+name))
            g.res['setup']['players']='Eight Kingdoms prepared 4v4; slot 0 human, seven AIs'
            return result
        return setup
    smoke.skirmish_setup=factory
    dll=ROOT/'local/runtime/bfme-host/extension/strategic.dll'
    pe=pefile.PE(str(dll));exports={e.name.decode():e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name};pe.close()
    old_game=smoke.Game
    class KingdomGame(old_game):
        def run(self,timeout,tick=None,tick_every=1.):
            def observe(g):
                frame,mode=g.logic()
                if mode!=2 or frame is None or frame<5 or not g.res.get('strategic_state_address'):
                    return tick(g) if tick else None
                module=g.res['strategic_state_address']-exports['bfxState']
                address=module+exports['bfxKingdoms'];movie=module+exports['bfxMovie']
                state=dict(zip(STATE_FIELDS,struct.unpack('<11I',g.read(address,44))))
                state['owned']=list(struct.unpack('<8I',g.read(address+76,32)))
                state['completedBuildings'],state['alliedPairs']=struct.unpack('<2I',g.read(address+108,8))
                for i,name in enumerate(('initialFrontMembers','frontMembers','frontMoved')):
                    state[name]=list(struct.unpack('<4I',g.read(address+116+i*16,16)))
                state['frontCasualties']=[max(0,a-b) for a,b in zip(state['initialFrontMembers'],state['frontMembers'])]
                for i,name in enumerate(('heavySpawned','heavyAlive','heavyMoved','heavyOrders')):
                    state[name]=g.u32(address+164+i*4)
                g.res['kingdoms_battle']=state
                g.res['battalion_symbols']=dict(zip(('enabled','collapsed','peakCollapsed'),
                    struct.unpack('<3I',g.read(module+exports['bfxBattalionSymbols'],12))))
                if state['error']:return 'kingdoms-battle-error'
                if not g.res.get('kingdoms_requested'):
                    from scenarios.eight_player import census
                    g.res['player_census']=census(g)
                    owners={};obj=g.u32(g.u32(g.base+0x9FE78C)+0xac);seen=set()
                    while obj and obj not in seen:
                        seen.add(obj);team=g.u32(obj+0x304);proto=g.u32(team+0x30) if team else 0
                        owner=g.u32(proto+8) if proto else 0
                        if owner:
                            index=g.u32(owner+0x54)
                            if 3<=index<=10:owners[index]=owner
                        obj=g.u32(obj+0x8c)
                    if len(owners)!=8:raise RuntimeError('Eight native players were not instantiated')
                    g.write(address+8,struct.pack('<I',len(config['units'])))
                    g.write(address+44,struct.pack('<8I',*[owners[i] for i in range(3,11)]))
                    blob=b''.join(struct.pack('<3I7f64s',u['player'],u['horde'],u['release'],
                        *u['position'],*u['destination'],u['angle'],u['name'].encode()) for u in config['units'])
                    g.write(module+exports['bfxKingdomUnits'],blob)
                    g.arm('GameEngine::update',lambda game,tid,ctx:{'call':module+exports['bfxKingdomsStart'],'ecx':0})
                    g.res['kingdoms_requested']=frame;g.res['authored_map_sha256']=config['map_sha256']
                elif state['stage']==2 and frame>=g.res.get('kingdoms_probe_frame',0)+5:
                    g.arm('GameEngine::update',lambda game,tid,ctx:{'call':module+exports['bfxKingdomsProbe'],'ecx':0})
                    g.res['kingdoms_probe_frame']=frame
                if record and state['stage']==2 and not g.res.get('kingdoms_recording'):
                    from capture.kingdoms import start_recording
                    start_recording(g,module,exports,config,OUT)
                if record:
                    mv=dict(zip(['enabled','frames','error','complete','limit','exitCode','shots'],struct.unpack('<7I',g.read(movie,28))))
                    mv['strategicFrames'],mv['peakIcons']=struct.unpack('<2I',g.read(movie+2076,8))
                    g.res['kingdoms_movie']=mv
                    if mv['error']:return 'kingdoms-movie-error'
                    if mv['complete']:return 'kingdoms-trailer-complete'
                (OUT/'battle-live.json').write_text(json.dumps(dict(frame=frame,battle=state,movie=g.res.get('kingdoms_movie')),indent=2))
                return tick(g) if tick else None
            return super().run(timeout,observe,tick_every=.25)
    smoke.Game=KingdomGame
    if record:
        old_tick=smoke.skirmish_tick
        def tick_factory(args,samples,mode):
            args.seconds=240
            return old_tick(args,samples,mode)
        smoke.skirmish_tick=tick_factory



def validate(output):
    from scenarios.validation import validate as check
    return check(output,capture=OUT,destination=VALIDATION_OUT)
