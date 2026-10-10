"""Tile the native renderer into an 8000-square tilted map photograph.

Each 1600x1200 frame contributes its HUD-free upper 720 rows. The orthographic
view plane moves by exactly that crop's world span; no generated/upscaled pixels.
"""

from common.paths import ROOT
import json
import math
from pathlib import Path
import struct

from PIL import Image

OUT=ROOT/'local/artifacts/ithilien-frontier/photo'
SIZE=8000
TILE_W,TILE_H=1600,720
TITLE='Ithilien-Frontier'
FOCUS=(4200,4765,50)


def register(smoke,tour=None):
    global OUT,TITLE,FOCUS
    if tour:
        config=json.loads(tour.read_text())
        OUT=ROOT/config['photo_output']
        TITLE=config['photo_name'];FOCUS=tuple(config['photo_focus'])
    original=smoke.skirmish_tick
    original_run=smoke.Game.run
    def run(self,timeout,tick=None,tick_every=1.0):
        return original_run(self,timeout,tick,tick_every=.15)
    smoke.Game.run=run
    OUT.mkdir(parents=True,exist_ok=True)
    def factory(args,samples,mode):
        args.seconds=165
        basic=original(args,samples,mode)
        stage=0;pending=False;next_frame=5;positioned=False;initialized=False
        tiles=[(x,y) for y in range(0,SIZE,TILE_H) for x in range(0,SIZE,TILE_W)]
        def tick(game):
            nonlocal stage,pending,next_frame,positioned,initialized
            basic(game)
            frame,current=game.logic()
            if current!=mode or frame is None or frame<3:return None
            if not initialized:
                def reveal(g,tid,ctx):
                    player=g.u32(g.u32(g.base+0x9FEEE8)+0x10)
                    return {'call':g.base+0x739790,'ecx':g.u32(g.base+0x9FE74C),'args':[g.u32(player+0x54)]}
                game.arm('GameEngine::update',reveal)
                initialized=True;next_frame=frame+8
            if pending:
                request,status,w,h,pitch,pixels=struct.unpack('<6I',game.read(game.res['capture_address'],24))
                if not request:
                    if status or not pixels or (w,h)!=(1600,1200):raise RuntimeError('Unexpected native photo surface')
                    picture=Image.frombytes('RGB',(w,h),game.read(pixels,pitch*h),'raw','BGRX',pitch,1)
                    x,y=tiles[stage]
                    picture.crop((0,0,TILE_W,min(TILE_H,SIZE-y))).save(OUT/f'tile-{x}-{y}.png')
                    stage+=1;pending=False;positioned=False;next_frame=frame+1
                    (OUT/'progress.json').write_text(json.dumps(dict(completed=stage,total=len(tiles))))
                    print(f'Native photo tile {stage}/{len(tiles)}',flush=True)
                    if stage==len(tiles):
                        game.write(game.res['photo_address'],bytes(4))
                        game.res['photo_tiles']=stage
                        return 'photo-complete'
            if stage<len(tiles) and frame>=next_frame and not pending:
                if not positioned:
                    x,y=tiles[stage]
                    # 1.25 world units per final pixel; camera is 20 degrees off vertical.
                    left=-5000+x*1.25;top=5000-y*1.25
                    game.write(game.res['photo_address'],struct.pack('<I8f',1,*FOCUS,
                               math.radians(70),left,top-1500,left+2000,top))
                    positioned=True;next_frame=frame+3
                else:
                    game.write(game.res['capture_address'],struct.pack('<I',1));pending=True
            # The native test's timeout still protects us; its short duration must
            # not interrupt a slow GPU before all tiles have rendered.
            return None
        return tick
    smoke.skirmish_tick=factory


def validate(output):
    report=json.loads((output/'skirmish_retail.json').read_text())
    run=report['run']
    if (run.get('photo_tiles')!=60 or run.get('stopped')!='photo-complete'
            or run.get('strategic',{}).get('faults',1) or report.get('profile_touched')
            or not any(f and f>=100 and m==2 for _,f,m in report['samples'])):
        raise RuntimeError('Incomplete native map photo; inspect skirmish_retail.json')
    image=Image.new('RGB',(SIZE,SIZE))
    for y in range(0,SIZE,TILE_H):
        for x in range(0,SIZE,TILE_W):
            with Image.open(OUT/f'tile-{x}-{y}.png') as tile:image.paste(tile,(x,y))
    image.save(OUT/(TITLE+'-8000.png'))
    image.save(OUT/(TITLE+'-8000.jpg'),quality=95,subsampling=0)
    image.thumbnail((1600,1600));image.save(OUT/'preview.jpg',quality=93)
    (OUT/'capture.json').write_text(json.dumps(dict(native=True,width=SIZE,height=SIZE,tiles=60,
        elevation_degrees=70,projection='orthographic',hud='excluded by tile framing',
        upscaled=False,extension_faults=0),indent=2))
    return 0
