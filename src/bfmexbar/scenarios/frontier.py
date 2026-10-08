"""One-time native reveal and initial camera for the authored frontier map."""

from bfmexbar.paths import ROOT
import struct
import json


def tick(game,smoke,title='Ithilien Frontier'):
    frame,mode=game.logic()
    if mode!=2 or frame is None or frame<3 or game.res.get('frontier_initialized'):return
    def ready(g,results):
        g.res['frontier_ready']=True
        (smoke.OUT/'frontier-live.json').write_text(json.dumps({
            'ready':True,'pid':g.pid,'frame':g.logic()[0],
            'factions':g.res.get('battle_factions'),'revealed':True,
            'camera_height':900,'map':title,
        },indent=2))
    def setup(g,tid,ctx):
        player=g.u32(g.u32(g.base+0x9FEEE8)+0x10)
        view=g.u32(g.base+0x9FEA3C)
        return {'calls':[{'call':g.base+0x739790,'ecx':g.u32(g.base+0x9FE74C),'args':[g.u32(player+0x54)]},
                         {'call':g.base+0x8D2B8,'ecx':view,'args':[struct.unpack('<I',struct.pack('<f',900))[0]]}],
                'done':ready}
    game.arm('GameEngine::update',setup)
    game.res['frontier_initialized']=True
