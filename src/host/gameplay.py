"""Native BFME2 1.06 direct-skirmish economy setup and startup readback.

GameInfoReset.cpp and MpGameRules.cpp in the read-only openbfme2 reference
place initial resources at GameInfo +0x70 and the CP percentage at +0x6C.
PlayerInitFromDict.cpp places money at Player +0x94; retail 0x2A71BC
initializes CP base/ceiling at Player +0x64/+0x70. The launcher verifies
the full game.dat hash before registering these hooks.
"""
import json
import struct


def register(smoke,starting_cash):
    original=smoke.skirmish_setup
    def factory(*args,**kwargs):
        handler=original(*args,**kwargs)
        def setup(game,tid,ctx):
            result=handler(game,tid,ctx)
            info=game.global_ptr('TheSkirmishGameInfo')
            if not info:raise RuntimeError('Skirmish settings are missing')
            # The direct -file path skips the menu. Set its native options
            # before Player::init consumes them; do not refill cash each tick.
            for offset,value in ((0x70,starting_cash),(0x6C,100)):
                data=struct.pack('<I',value)
                if not game.write(info+offset,data) or game.read(info+offset,4)!=data:
                    raise RuntimeError('Cannot apply native skirmish economy settings')
            game.res['bfmexbar_gameplay']={'startingCash':starting_cash,'commandPointPercent':100}
            return result
        return setup
    smoke.skirmish_setup=factory

    original_game=smoke.Game
    # PlayerList::update has its own breakpoint, independent of the camera,
    # battle, and map tools sharing GameEngine::update.
    smoke.RVA['bmfe-workshopGameplayRead']=0x2A7AB6
    class GameplayGame(original_game):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self.on('bmfe-workshopGameplayRead',self.read_startup)

        @staticmethod
        def read_startup(game,tid,ctx):
            frame,mode=game.logic()
            if mode!=2 or frame is None or frame<1:return True
            settings=game.res.get('bfmexbar_gameplay')
            if settings is None:return False  # Menu launches keep menu options.
            info=game.global_ptr('TheSkirmishGameInfo')
            players=game.u32(game.base+0x9FEEE8)
            actual=[]
            for i in range(8):
                slot=game.u32(info+smoke.SLOTS_OFF+4*i)
                if not slot or game.u32(slot+smoke.SLOT_STATE) not in (2,3,4,5,6):continue
                if game.u32(slot+smoke.SLOT_TEMPLATE)==0xFFFFFFFE:continue  # Observer.
                # PlayerList's array starts at +0x18; index 0 is neutral,
                # skirmish slot 0 is player index 1.
                player=game.u32(players+0x18+4*(i+1))
                if not player:raise RuntimeError('Skirmish player is missing')
                actual.append({'slot':i,'cash':game.u32(player+0x94),
                               'commandPoints':game.u32(player+0x64),
                               'commandPointCeiling':game.u32(player+0x70)})
            settings.update(frame=frame,players=actual)
            (smoke.OUT/'gameplay-startup.json').write_text(json.dumps(settings,indent=2))
            return False
    smoke.Game=GameplayGame


def validate(output,limits,starting_cash):
    report=json.loads((output/'skirmish_retail.json').read_text())
    settings=report['run'].get('bfmexbar_gameplay',{})
    players=settings.get('players',[])
    count=max(2,len(players))
    expected={tuple(limits[f'{faction}CommandPointsMP{count}']) for faction in ('Good','Evil')} if count<=8 else set()
    failures=[]
    if not players:failures.append('No native economy readback')
    for player in players:
        if player['cash']!=starting_cash:
            failures.append(f'Slot {player["slot"]}: incorrect starting money')
        if (player['commandPoints'],player['commandPointCeiling']) not in expected:
            failures.append(f'Slot {player["slot"]}: incorrect command-point capacity')
    (output/'gameplay-regression.json').write_text(json.dumps({
        'outcome':'fail' if failures else 'pass','failures':failures,'startup':settings},indent=2))
    if failures:print('Gameplay check failed: '+'; '.join(failures),flush=True)
    return 1 if failures else 0
