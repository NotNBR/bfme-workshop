"""Test-only native builder movement across authored bridge spans.

Uses the same version-checked Object::setPosition and AI attack-move calls as
the existing prepared-battle harness. Never registered for interactive play.
"""

from bfmexbar.paths import ROOT
import ctypes
import math
import struct


def begin(game, probes):
    local=game.u32(game.u32(game.base+0x9FEEE8)+0x10)
    obj=game.u32(game.u32(game.base+0x9FE78C)+0xAC)
    actors=[];visited=set()
    while obj and obj not in visited:
        visited.add(obj)
        template=game.u32(obj+4);ai=game.u32(obj+0x258);team=game.u32(obj+0x304)
        prototype=game.u32(team+0x30) if team else 0
        owner=game.u32(prototype+8) if prototype else 0
        if owner==local and template and ai:
            kinds=game.read(template+0x108,26)
            if kinds[14//8]&(1<<(14%8)) or kinds[143//8]&(1<<(143%8)):
                actors.append((obj,ai))
        obj=game.u32(obj+0x8C)
    if len(actors)<len(probes):
        raise RuntimeError('Not enough local mobile builders for bridge probes')
    memory=game.k.VirtualAllocEx(ctypes.c_void_p(game.hproc),None,24*len(probes),0x3000,4)
    if not memory:raise RuntimeError('Cannot allocate bridge probe coordinates')
    calls=[];states=[]
    for i,(probe,(obj,ai)) in enumerate(zip(probes,actors)):
        source=probe['source'];destination=probe['destination'];address=memory+24*i
        game.write(address,struct.pack('<6f',*source,*destination))
        calls += [dict(call=game.base+0x30AA80,ecx=obj,args=[address]),
                  dict(call=game.base+0x295A0F,ecx=ai+0x20,args=[address+12,0x7fffffff,2])]
        states.append(dict(name=probe['name'],object=obj,source=source,destination=destination,
                           center=probe['center'],samples=[],reached=False,passed_over_deck=False))
    def done(g,results):g.res['bridge_probes']=states
    return dict(calls=calls,done=done)


def sample(game,frame):
    for probe in game.res.get('bridge_probes',[]):
        if probe['reached']:continue
        position=struct.unpack('<3f',game.read(probe['object']+0x38,12))
        probe['samples'].append(dict(frame=frame,position=position))
        if math.dist(position[:2],probe['center'][:2])<100:
            probe['passed_over_deck']=True
        probe['remaining_distance']=math.dist(position[:2],probe['destination'][:2])
        probe['reached']=probe['remaining_distance']<65 and probe['passed_over_deck']
