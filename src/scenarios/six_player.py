"""Normal six-player open skirmish: one human and five easy AI opponents."""
from scenarios.eight_player import census
import re
import struct

FACTIONS=['Men','Elves','Dwarves','Isengard','Mordor','Wild']


def register(smoke,mod):
    names=re.findall(r'^PlayerTemplate\s+(\w+)',(mod/'data/ini/playertemplate.ini').read_text(encoding='cp1252'),re.M)
    factions=[names.index('Faction'+name) for name in FACTIONS]
    original=smoke.skirmish_setup
    def factory(*args,**kwargs):
        handler=original(*args,**kwargs)
        def setup(game,tid,ctx):
            result=handler(game,tid,ctx)
            info=game.global_ptr('TheSkirmishGameInfo')
            if not info:raise RuntimeError('Six-player skirmish info missing')
            actual=[]
            for i in range(8):
                slot=game.u32(info+smoke.SLOTS_OFF+4*i)
                if not slot:raise RuntimeError(f'Missing native slot {i}')
                if i>=6:
                    game.write(slot+smoke.SLOT_STATE,struct.pack('<I',0))
                    continue
                if i:
                    game.write(slot+smoke.SLOT_STATE,struct.pack('<I',smoke.AI_STATES['easy']))
                    game.write(slot+8,b'\x01\x01')
                game.write(slot+smoke.SLOT_TEMPLATE,struct.pack('<i',factions[i]))
                actual.append(dict(slot=i,faction=FACTIONS[i],state=game.u32(slot+smoke.SLOT_STATE),template=factions[i]))
            game.res['six_player_slots']=actual
            game.res['setup']['players']='slot 0 human, slots 1..5 easy AI, slots 6..7 closed'
            return result
        return setup
    smoke.skirmish_setup=factory
