"""Fill all eight native skirmish slots without modifying the reference helper."""

from common.paths import ROOT
import re
import struct

FACTIONS=['Men','Elves','Dwarves','Isengard','Mordor','Wild','Men','Elves']


def register(smoke,mod):
    names=re.findall(r'^PlayerTemplate\s+(\w+)',(mod/'data/ini/playertemplate.ini').read_text(encoding='cp1252'),re.M)
    factions=[names.index('Faction'+name) for name in FACTIONS]
    original=smoke.skirmish_setup
    def factory(*args,**kwargs):
        handler=original(*args,**kwargs)
        def setup(game,tid,ctx):
            result=handler(game,tid,ctx)
            info=game.global_ptr('TheSkirmishGameInfo')
            if not info:raise RuntimeError('Eight-player skirmish info missing')
            actual=[]
            for i,faction in enumerate(factions):
                slot=game.u32(info+smoke.SLOTS_OFF+4*i)
                if not slot:raise RuntimeError(f'Missing native slot {i}')
                if i:
                    game.write(slot+smoke.SLOT_STATE,struct.pack('<I',smoke.AI_STATES['easy']))
                    game.write(slot+8,b'\x01\x01')
                game.write(slot+smoke.SLOT_TEMPLATE,struct.pack('<i',faction))
                actual.append(dict(slot=i,faction=FACTIONS[i],state=game.u32(slot+smoke.SLOT_STATE),
                                   template=game.u32(slot+smoke.SLOT_TEMPLATE)))
            game.res['eight_player_slots']=actual
            game.res['setup']['players']='slot 0 human, slots 1..7 easy AI'
            return result
        return setup
    smoke.skirmish_setup=factory


def census(game):
    """Read instantiated object owners once, independent of configured slots."""
    obj=game.u32(game.u32(game.base+0x9FE78C)+0xAC)
    owners={};builders={};teams={};templates={};seen=set()
    while obj and obj not in seen and len(seen)<30000:
        seen.add(obj)
        data=game.read(obj,0x308)
        team=struct.unpack_from('<I',data,0x304)[0]
        if team not in teams:
            prototype=game.u32(team+0x30) if team else 0
            owner=game.u32(prototype+8) if prototype else 0
            teams[team]=game.u32(owner+0x54) if owner else None
        index=teams[team]
        if index is not None:owners[index]=owners.get(index,0)+1
        template=struct.unpack_from('<I',data,4)[0]
        if template and template not in templates:
            kinds=game.read(template+0x108,26)
            templates[template]=bool(kinds[14//8]&(1<<(14%8)) or kinds[143//8]&(1<<(143%8)))
        if index is not None and templates.get(template):builders[index]=builders.get(index,0)+1
        obj=struct.unpack_from('<I',data,0x8C)[0]
    return dict(objects=len(seen),owner_counts=owners,builder_owners=builders)
