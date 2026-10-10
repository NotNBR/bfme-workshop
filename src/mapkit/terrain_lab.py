"""Build an isolated native terrain experiment, never a production-map pass."""

import argparse
import json
import math
from pathlib import Path
import struct

import numpy as np
from PIL import Image

from common.paths import ROOT
from formats.map import Reader, sha, tile_offset
from mapkit.blank import create, set_heights, set_materials, starts
from mapkit.analyze import analyze


NAME = 'map mp bfmexbar terrain lab'
PALETTE = ['DirtMordor04', 'GrassMediumType40', 'SnowCaradhras03', 'CliffMediumType16b']
BORDER = 8
UV_STEP = 32 / 2048  # Experimental Generals atlas scale; not a production default.


def build():
    m = create(192, 192, BORDER, title='BFME Workshop Terrain Lab')
    size = 192 + 2 * BORDER
    labels = np.zeros((size, size), dtype='u2')
    heights = np.full((size, size), 100.)
    planes = {k: np.zeros((size, size), dtype='<u4') for k in ('blends', 'three_way', 'cliffs')}
    blends, cliffs, cases = [], [], []
    lookup = {}

    def blend(tile, direction, flags=0, long=0):
        key = (tile, direction, flags, long)
        if key not in lookup:
            switch = bytes(int(i == direction) for i in range(4))
            blends.append(struct.pack('<I4sBBiI', tile, switch, flags, long, -1, 0x7ada0000))
            lookup[key] = len(blends)
        return lookup[key]

    def panel(row, column, name):
        x, y = 12 + 46 * column, 28 + 40 * row
        cases.append(dict(name=name, rect_world=[x*10, y*10, (x+30)*10, (y+24)*10]))
        return x + BORDER, y + BORDER

    # Repeated isolated quads make each alpha-corner pattern visible without
    # an automatic material classifier choosing or altering the transition.
    patterns = [(0,0,0), (0,1,0), (1,0,0), (1,1,0),
                (2,0,0), (2,1,0), (3,0,0), (3,1,0),
                (2,0,1), (3,1,1)]
    names = ['east', 'west', 'north', 'south', 'right-diagonal', 'right-inverted',
             'left-diagonal', 'left-inverted', 'right-long', 'left-inverted-long']
    for i, ((direction, flags, long), name) in enumerate(zip(patterns, names)):
        x0, y0 = panel(i//4, i%4, name)
        labels[y0:y0+24, x0:x0+30] = 1
        for y in range(y0+2, y0+22, 3):
            for x in range(x0+2, x0+28, 3):
                tile = int(2*64 + tile_offset(x, y, 4))
                planes['blends'][y,x] = blend(tile, direction, flags, long)

    # Pair primary cardinal blends with a diagonal third layer. The second
    # example requires both layers to use the flipped cell diagonal.
    for column, flip in ((2, False), (3, True)):
        x0,y0 = panel(2, column, 'three-way-flipped' if flip else 'three-way-unflipped')
        for y in range(y0+2,y0+22,3):
            for x in range(x0+2,x0+28,3):
                phase = int(tile_offset(x,y,4))
                planes['blends'][y,x] = blend(64+phase, 0, 2 if flip else 0)
                planes['three_way'][y,x] = blend(128+phase, 2 if flip else 3)

    # Four identical east-facing triangular ridges: default engine projection,
    # explicit planar UV, and two candidate slope scales. Integer texture steps
    # keep every quad inside one material's atlas rectangle when wrapping.
    for column, scale in enumerate((None, 1, 2, 4)):
        name = 'cliff-default' if scale is None else f'cliff-uv-scale-{scale}'
        x0,y0 = panel(3,column,name)
        labels[y0:y0+25,x0:x0+31] = 3
        for y in range(y0,y0+25):
            for x in range(x0,x0+31):
                t = (x-x0) % 8
                heights[y,x] += min(t,8-t) * 10 * math.sqrt(3)
        if scale is None:
            continue
        for y in range(y0,y0+24):
            for x in range(x0,x0+30):
                u = ((x-x0)*scale % 8)*UV_STEP
                v = -((y-y0) % 8)*UV_STEP
                uv = [u,v, u+scale*UV_STEP,v, u+scale*UV_STEP,v-UV_STEP, u,v-UV_STEP]
                cliffs.append(struct.pack('<I8fBB', 3*64, *uv, 0, 0))
                planes['cliffs'][y,x] = len(cliffs)

    set_heights(m, heights)
    set_materials(m, PALETTE, labels, blend_edges=False)
    b = m.blend()
    data = bytearray(m.chunk('BlendTileData').data)
    for name, plane in planes.items():
        offset = b['offsets'][name]
        data[offset:offset+plane.nbytes] = plane.tobytes()
    # set_materials produced empty tables; replace their counts and append our records.
    struct.pack_into('<II', data, b['tail_offset']+4, len(blends)+1, len(cliffs)+1)
    m.chunk('BlendTileData').data = bytes(data) + b''.join(blends) + b''.join(cliffs)
    starts(m, [(250,100),(1650,100)])
    fields = m.properties(Reader(m.chunk('WorldInfo').data))
    m.chunk('WorldInfo').data = m.encode_properties([
        (k,t,'Isolated blend and cliff UV experiments; not a balanced skirmish map.' if k=='mapDescription' else v)
        for k,t,v in fields])
    return m, cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT/'local/artifacts/terrain-lab')
    parser.add_argument('--install', action='store_true', help='Copy only this generated map into the prepared mod')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    m,cases = build()
    data = m.encode()
    (out/(NAME+'.map')).write_bytes(data)
    report = analyze(data)
    report.update(cases=cases, worldbuilder_verified=False, native_render_verified=False,
                  experimental_uv_step=UV_STEP)
    (out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    tour = dict(output=str(out/'native'), map_sha256=sha(data), shots=[
        ['overview',960,960,3400], ['blends',960,580,1900],
        ['three-way',1370,1190,1050], ['cliffs',960,1610,1700]])
    (out/'tour.json').write_text(json.dumps(tour,indent=2)+'\n')
    if args.install:
        config = json.loads((ROOT/'local/runtime/bfme-host/manifest.json').read_text())
        target = Path(config['mod'])/'maps'/NAME
        target.mkdir(parents=True,exist_ok=True)
        path = target/(NAME+'.map')
        path.write_bytes(data)
        colors=np.array([[68,52,45],[100,125,65],[225,230,232],[135,137,130]],dtype='u1')
        pixels=colors[m.blend()['arrays']['tiles']//64][BORDER:-BORDER,BORDER:-BORDER]
        radar=Image.fromarray(pixels[::-1]).resize((256,256),Image.Resampling.NEAREST)
        for suffix in ('_art.tga','_pic.tga'):
            radar.save(target/(NAME+suffix))
        from mapkit.cache import cache_entry
        cache_entry(path,m,NAME,'BFME Workshop Terrain Lab','Isolated terrain rendering experiments.')
    print(json.dumps(dict(map=str(out/(NAME+'.map')), sha256=sha(data), cases=len(cases),
                          blend_records=report['blend_details']['blend_records'],
                          cliff_mappings=report['blend_details']['cliff_mappings'])))


if __name__ == '__main__':
    main()
