"""Build the native Ithilien Frontier map from locally installed BFME2 assets."""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import random
import re
import shutil
import struct
import zlib

import numpy as np

from .format import Map, Reader, chunks, string, sha, tile_offset
from .analyze import records, analyze
from .cli import preview
from .relief import sculpt

ROOT = Path(__file__).resolve().parents[2]
NAME = 'map mp bfmexbar ithilien frontier'


def cache_entry(path, m):
    cache=ROOT/'runtime/bfme-host/mod/maps/mapcache.ini'
    text=cache.read_text(encoding='cp1252')
    def escaped(raw):
        return ''.join(chr(c) if (48<=c<=57 or 65<=c<=90 or 97<=c<=122) else f'_{c:02X}' for c in raw)
    key=escaped(('maps\\'+NAME+'\\'+NAME+'.map').encode('ascii'))
    text=re.sub(r'(?ms)^MapCache '+re.escape(key)+r'\s*\n.*?^END\s*\n?', '',text)
    t=m.heightmap();w=(t['width']-2*t['border'])*10;h=(t['height']-2*t['border'])*10
    lines=[f'MapCache {key}',f'  fileSize = {path.stat().st_size}',
           f'  fileCRC = {zlib.crc32(path.read_bytes())}', '  timestampLo = 0','  timestampHi = 0',
           '  isOfficial = yes','  isMultiplayer = yes','  isScenarioMP = no','  numPlayers = 2',
           '  extentMin = X:0.00 Y:0.00 Z:0.00',f'  extentMax = X:{w:.2f} Y:{h:.2f} Z:0.00',
           '  displayName = '+escaped('Ithilien Frontier'.encode('utf-16-le')),
           '  description = '+escaped('A vast wooded frontier of Gondor, ancient ruins and four river crossings.'.encode('utf-16-le'))]
    for o in m.objects():
        for k,_,v in o['properties']:
            if k=='waypointName' and re.fullmatch(r'Player_\d+_Start',v):
                lines.append(f'  {v} = X:{o["x"]:.2f} Y:{o["y"]:.2f} Z:0.00')
    lines.append('END')
    cache.write_text(text.rstrip()+'\n\n'+'\n'.join(lines)+'\n',encoding='cp1252')


def water(m, sx, sy):
    for name in ('StandingWaterAreas', 'RiverAreas'):
        areas = records(m, name)
        out = bytearray(struct.pack('<I', len(areas)))
        for a in areas:
            out += struct.pack('<I', a['id']) + string(a['name']) + string(a['layer'])
            out += struct.pack('<fB', a['uv_speed'], a['additive'])
            if name == 'StandingWaterAreas':
                out += string(a['bump_texture']) + string(a['sky_texture'])
                out += struct.pack('<I', len(a['points']))
                for x, y in a['points']:
                    out += struct.pack('<2f', x * sx, y * sy)
                out += struct.pack('<I', a['water_height']) + string(a['shader']) + string(a['depth_colors'])
            else:
                for key in ('texture', 'noise', 'alpha_edge', 'sparkle'):
                    out += string(a[key])
                out += struct.pack('<4BfI', *a['color_bytes'], a['alpha'], a['water_height']) + string(a['min_lod'])
                out += struct.pack('<I', len(a['cross_sections']))
                for x1, y1, x2, y2 in a['cross_sections']:
                    out += struct.pack('<4f', x1 * sx, y1 * sy, x2 * sx, y2 * sy)
        m.chunk(name).data = bytes(out)


def resize(source, width=840, height=953):
    m = Map(source)
    if not isinstance(width,int) or not isinstance(height,int) or min(width,height)<64:
        raise ValueError('Playable dimensions must be integer tile counts of at least 64')
    # This authoring path intentionally supports the measured stock Ithilien layout.
    for name in ('TriggerAreas', 'StandingWaveAreas', 'CameraAnimationList', 'WaypointsList'):
        if m.chunk(name).data != bytes(4):
            raise ValueError(f'Nonempty {name} requires explicit coordinate handling')
    if any(c.data for c in chunks(m.chunk('PlayerScriptsList').data, m.names)):
        raise ValueError('Embedded scripts need coordinate review before resizing')
    t, b = m.heightmap(), m.blend()
    border = t['border']
    sx, sy = width / (t['width'] - 2 * border), height / (t['height'] - 2 * border)
    w, h = width + border * 2, height + border * 2
    if max(w, h) > 1024:
        raise ValueError('This experiment caps stored grids at 1024 samples per axis')
    # Resample only terrain. Native meshes, animation, units and texture scale stay native.
    fx = np.clip((np.arange(w) - border) / sx + border, 0, t['width'] - 1)
    fy = np.clip((np.arange(h) - border) / sy + border, 0, t['height'] - 1)
    ix, iy = np.rint(fx).astype(int), np.rint(fy).astype(int)
    x0, y0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
    x1, y1 = np.minimum(x0 + 1, t['width'] - 1), np.minimum(y0 + 1, t['height'] - 1)
    wx, wy = fx - x0, fy - y0
    old = t['elevations'].astype(float)
    rows = old[:, x0] * (1 - wx) + old[:, x1] * wx
    elevations = np.rint(rows[y0] * (1 - wy[:, None]) + rows[y1] * wy[:, None]).astype('<u2')
    m.chunk('HeightMapData').data = struct.pack('<7I', w, h, border, 1, width, height, w*h) + elevations.tobytes()
    arrays = {key: value[iy[:, None], ix[None, :]].copy() for key, value in b['arrays'].items()}
    yy, xx = np.indices((h, w))
    # Rephase primary texture cells so 3x more terrain does not stretch the ground art.
    for tex in b['textures']:
        mask = (arrays['tiles'] >= tex['tile_start']) & (arrays['tiles'] < tex['tile_start'] + tex['tile_count'])
        arrays['tiles'][mask] = tex['tile_start'] + tile_offset(xx[mask],yy[mask],tex['cell_size'])
    r = Reader(m.chunk('BlendTileData').data)
    r.take(b['tail_offset'])
    cells, blend_count, cliff_count, tex_count = r.get('4I')
    palette_start = r.pos
    for _ in range(tex_count):
        r.get('4I'); r.string()
    r.get('2I')
    palette = r.data[palette_start:r.pos]
    old_blends = [r.take(18) for _ in range(max(0, blend_count - 1))]
    cliff_tail = r.take(len(r.data) - r.pos)
    # A blend points at a secondary texture cell. Rephase those cells as well.
    phase = (yy % 8) * 8 + xx % 8
    keys = np.unique(np.concatenate([a.ravel().astype('uint64') * 64 + phase.ravel()
                                    for a in (arrays['blends'], arrays['three_way'])]))
    keys = keys[keys >= 64]
    new_blends = []
    for key in keys:
        index, p = divmod(int(key), 64)
        original = old_blends[index - 1]
        tile = struct.unpack_from('<I', original)[0]
        tex = next(t for t in b['textures'] if t['tile_start'] <= tile < t['tile_start'] + t['tile_count'])
        tile = tex['tile_start'] + tile_offset(p%8,p//8,tex['cell_size'])
        new_blends.append(struct.pack('<I', tile) + original[4:])
    for name in ('blends', 'three_way'):
        key = arrays[name].astype('uint64') * 64 + phase
        arrays[name] = np.where(arrays[name] != 0, np.searchsorted(keys, key) + 1, 0).astype('<u4')
    out = bytearray(struct.pack('<I', w*h))
    for name in ('tiles', 'blends', 'three_way', 'cliffs'):
        out += arrays[name].tobytes()
    for name in ('impassable', 'impassable_players', 'passage_widths', 'taintable', 'extra_passable', 'flammability', 'visible'):
        out += arrays[name].tobytes() if name == 'flammability' else np.packbits(arrays[name], axis=1, bitorder='little').tobytes()
    out += struct.pack('<4I', cells, len(new_blends) + 1, cliff_count, tex_count) + palette + b''.join(new_blends) + cliff_tail
    m.chunk('BlendTileData').data = bytes(out)
    object_chunks = chunks(m.chunk('ObjectsList').data, m.names)
    for c in object_chunks:
        x, y = struct.unpack_from('<2f', c.data)
        c.data = struct.pack('<2f', x*sx, y*sy) + c.data[8:]
    m.chunk('ObjectsList').data = b''.join(c.encode() for c in object_chunks)
    water(m, sx, sy)
    cameras = records(m, 'NamedCameras')
    out = bytearray(struct.pack('<I', len(cameras)))
    for c in cameras:
        x, y, z = c['look_at']
        out += struct.pack('<3f', x*sx, y*sy, z) + string(c['name'])
        out += struct.pack('<6f', *(c[k] for k in ('pitch','roll','yaw','zoom','field_of_view','unknown')))
    m.chunk('NamedCameras').data = bytes(out)
    r = Reader(m.chunk('WorldInfo').data)
    fields = m.properties(r)
    fields = [(k, kind, 16000.0 if k == 'cameraMaxHeight' else ('Ithilien Frontier' if k == 'mapName' else v)) for k,kind,v in fields]
    m.chunk('WorldInfo').data = m.encode_properties(fields)
    return m


def detail(m, seed=20261008, count=4200):
    rng = random.Random(seed)
    objects = m.objects()
    donors = {o['template']:o for o in objects if o['flags'] == 0}
    t, b = m.heightmap(), m.blend()
    border = t['border']; width=(t['width']-border*2)*10; height=(t['height']-border*2)*10
    elevations=t['elevations'].astype(float)*0.0390625
    dy,dx=np.gradient(elevations,10);slope=np.hypot(dx,dy)
    centers=[o for o in objects if o['template'].startswith(('Tree','PTree','OptBush','GladdenFieldsShrub'))]
    ruins=[o for o in objects if o['template'].startswith(('GondorBuilding','OsgiliathRuin'))]
    starts=[o for o in objects if o['template']=='SkirmishSpawnPoint']
    # Native road endpoint order is retained by resize; use its segments as exclusions.
    roads=[];pending=None
    for o in objects:
        if o['flags']&2:pending=o
        elif o['flags']&4 and pending:
            roads.append((pending['x'],pending['y'],o['x'],o['y']));pending=None
    grid=defaultdict(list)
    def reserve(x,y):grid[(int(x//80),int(y//80))].append((x,y))
    for o in objects:reserve(o['x'],o['y'])
    def clear(x,y,gap):
        if not 100<x<width-100 or not 100<y<height-100:return False
        gx,gy=round(x/10)+border,round(y/10)+border
        if b['arrays']['impassable'][gy,gx] or elevations[gy,gx]<35 or slope[gy,gx]>.45:return False
        if any((x-o['x'])**2+(y-o['y'])**2<650**2 for o in starts):return False
        for ax,ay,bx,by in roads:
            vx,vy=bx-ax,by-ay
            q=max(0,min(1,((x-ax)*vx+(y-ay)*vy)/max(1,vx*vx+vy*vy)))
            if (x-ax-q*vx)**2+(y-ay-q*vy)**2<135**2:return False
        cellx,celly=int(x//80),int(y//80);n=math.ceil(gap/80)
        return not any((x-px)**2+(y-py)**2<gap*gap for cy in range(celly-n,celly+n+1) for cx in range(cellx-n,cellx+n+1) for px,py in grid[(cx,cy)])
    added=Counter()
    groups=[(['TreeEvergreen03','PTree09_Med','PTree10_Large','Tree03a','Tree01_L'],.60,42),
            (['OptBush03','OptBush01','GladdenFieldsShrub01','OptGrass08','OptGrass09'],.27,23),
            (['DarkRockGrey02','DarkRockGrey07','TreeDead01','TreeDead02'],.10,48),
            (['GondorBuildingIthilien17','GondorBuildingIthilien48','OsgiliathRuin06','OsgiliathRuin24'],.03,95)]
    for templates,fraction,gap in groups:
        wanted=round(count*fraction);placed=0
        if wanted == 0:continue
        for _ in range(wanted*80):
            center=rng.choice(ruins if fraction==.03 else centers)
            angle=rng.random()*math.tau;radius=math.sqrt(rng.random())*(240 if fraction==.03 else 300)
            x,y=center['x']+math.cos(angle)*radius,center['y']+math.sin(angle)*radius
            if not clear(x,y,gap):continue
            template=rng.choice(templates)
            m.append_object(donors[template],x,y,rng.random()*math.tau,f'BFX_Frontier_{sum(added.values())}')
            reserve(x,y);added[template]+=1;placed+=1
            if placed>=wanted:break
    return dict(added=dict(added),count=sum(added.values()),protected_base_radius=650,protected_road_half_width=135)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--detail',type=int,default=4200)
    p.add_argument('--width',type=int,default=840);p.add_argument('--height',type=int,default=953)
    args=p.parse_args()
    if not 0<=args.detail<=10000:p.error('Detail count must be 0..10000')
    source=ROOT/'runtime/bfme-host/mod/maps/map wor ithilien/map wor ithilien.map'
    original=source.read_bytes();m=resize(original,args.width,args.height)
    relief=sculpt(m)
    scenery=detail(m,count=args.detail) if args.detail else dict(count=0)
    data=m.encode();report=analyze(data)
    if report['unresolved_sections']:raise ValueError(report['unresolved_sections'])
    target=ROOT/'runtime/bfme-host/mod/maps'/NAME;target.mkdir(parents=True,exist_ok=True)
    path=target/(NAME+'.map');path.write_bytes(data)
    for suffix in ('_art.tga','_pic.tga'):
        donor=source.with_name(source.stem+suffix)
        if donor.exists():shutil.copy2(donor,target/(NAME+suffix))
    cache_entry(path,m)
    # Native distance fog would obscure the new strategic view at the stock 2000 units.
    (target/'map.ini').write_text('; bfmeXbar Ithilien Frontier\nWaterTransparency\n  ReflectionPlaneZ = 25\n  ReflectionOn = Yes\nEnd\nWeather\n  HardwareFogEnable = No\nEnd\nAIData\n  LowLodTreeName = TreeLowLODGreyHavens\nEnd\n',encoding='ascii')
    output=ROOT/'artifacts/ithilien-frontier';output.mkdir(parents=True,exist_ok=True)
    report.update(source_sha256=sha(original),scenery=scenery,relief=relief,area_vs_grey=args.width*args.height/266750)
    (output/'build.json').write_text(json.dumps(report,indent=2))
    preview(path,output/'overview.png')
    if source.read_bytes()!=original:raise AssertionError('Source changed')
    print(json.dumps(dict(map=str(path),size=report['dimensions'],objects=report['objects'],extra=scenery,area_vs_grey=report['area_vs_grey'])))


if __name__=='__main__':main()
