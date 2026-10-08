"""Build a native Recoil game using assets from a local BFME II install."""
import argparse
import io
import json
import math
import pathlib
import shutil
import struct
import sys

import numpy as np
from PIL import Image

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from bfmexbar.formats.big import BigArchive, convert
from legacy.recoil.tools.w3d import animation, skeleton, meshes, BASIS

UNITS = {
    'gondor': ('gumaarms_skn', 'gumaarms_skl', 'gumaarms', 'soldier'),
    'mordor': ('muorcwar_skn', 'muorcwarr_skl', 'muorcwarr', 'orc'),
}


def lua(value):
    if isinstance(value, dict):
        return '{'+','.join('['+json.dumps(str(k))+']='+lua(v) for k, v in value.items())+'}'
    if isinstance(value, (list, tuple)):
        return '{'+','.join(lua(v) for v in value)+'}'
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (float, np.floating)):
        if not math.isfinite(value):
            raise ValueError('Nonfinite number in generated Lua')
        return f'{value:.7g}'
    return str(value)


def s3o(path, groups, bones, texture, regions, scale):
    data = bytearray(52)
    def append(payload):
        offset = len(data); data.extend(payload); return offset
    def string(text):
        return append(text.encode('ascii')+b'\0')
    tex1, tex2 = string(texture+'.png'), string(texture+'_material.png')
    root = append(bytes(52))
    rootname = string('root')
    childtable = append(bytes(len(bones)*4))
    pieces = []
    for i, bone in enumerate(bones):
        offset = append(bytes(52)); pieces.append(offset)
        name = string('bone'+str(i))
        vertices = []
        for group in groups:
            if group['bone'] != i:
                continue
            x, y, w, h, atlasw, atlash = regions[group['texture']]
            for v in group['vertices']:
                # Pixel inset prevents texture bleeding between atlas regions.
                u = (x + .5 + np.clip(v[6], 0, 1)*(w-1))/atlasw
                # Recoil uploads PNG rows from the top without flipping S3O
                # textures. Preserve W3D's top-origin V coordinates.
                t = (y + .5 + np.clip(v[7], 0, 1)*(h-1))/atlash
                vertices.append([*v[:6], u, t])
        vertexptr = append(np.array(vertices, dtype='<f4').tobytes())
        # Positive-determinant basis conversion preserves W3D face winding.
        indices = list(range(len(vertices)))
        indexptr = append(struct.pack('<'+'I'*len(indices), *indices))
        struct.pack_into('<10i3f', data, offset, name, 0, 0, len(vertices), vertexptr, 0, 0, len(indices), indexptr, 0, 0, 0, 0)
    struct.pack_into('<'+'i'*len(pieces), data, childtable, *pieces)
    struct.pack_into('<10i3f', data, root, rootname, len(bones), childtable, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    struct.pack_into('<12si5f4i', data, 0, b'Spring unit\0', 0, 22*scale, 28*scale, 0, 12*scale, 0, root, 0, tex1, tex2)
    path.write_bytes(data)


def make_atlas(groups, archives, out, name):
    textures = sorted(set(g['texture'] for g in groups))
    images = []
    for filename in textures:
        stem = pathlib.Path(filename).stem
        matches = [(a, k) for a in archives for k in a.entries if pathlib.PurePosixPath(k).stem == stem and k.endswith(('.dds', '.tga'))]
        if not matches:
            raise ValueError('Missing original texture '+filename)
        archive, key = matches[0]
        images.append(Image.open(io.BytesIO(archive.read_bytes(key))).convert('RGBA'))
    width = 2**math.ceil(math.log2(max(im.width for im in images)))
    height = 2**math.ceil(math.log2(sum(im.height for im in images)))
    atlas = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    material = Image.new('RGBA', (width, height), (0, 0, 0, 255))
    regions, y = {}, 0
    for filename, im in zip(textures, images):
        opacity = im.getchannel('A')
        mat = Image.new('RGBA', im.size, (0, 22, 0, 255)); mat.putalpha(opacity)
        material.paste(mat, (0, y))
        im.putalpha(0)  # S3O texture1 alpha is team colour, not transparency.
        atlas.paste(im, (0, y))
        regions[filename] = (0, y, im.width, im.height, width, height)
        y += im.height
    atlas.save(out/(name+'.png')); material.save(out/(name+'_material.png'))
    return regions


def bc1_color(rgb):
    r, g, b = rgb
    value = (r>>3)<<11 | (g>>2)<<5 | (b>>3)
    return struct.pack('<HHI', value, value, 0)


def make_map(output):
    """Write an uncompressed SMF container and valid BC1 SMT texture tiles."""
    folder = output/'maps'; folder.mkdir(parents=True, exist_ok=True)
    size = 512
    colors = [(75+i*2, 85+i*2, 49+i) for i in range(16)]
    tiles = bytearray(struct.pack('<16s4i', b'spring tilefile\0', 1, len(colors), 32, 1))
    for color in colors:
        for resolution in (32, 16, 8, 4):
            tiles.extend(bc1_color(color)*(resolution//4)**2)
    (folder/'pelennor.smt').write_bytes(tiles)
    data = bytearray(80)
    def append(payload):
        offset = len(data); data.extend(payload); return offset
    y, x = np.mgrid[0:size+1, 0:size+1]
    elevation = 16 + 4*np.sin(x/33)*np.cos(y/47) + 2*np.sin((x+y)/15)
    heightptr = append((elevation/64*65535).astype('<u2').tobytes())
    typeptr = append(bytes((size//2)**2))
    tileptr = append(struct.pack('<3i', 1, len(colors), len(colors))+b'pelennor.smt\0')
    yy, xx = np.mgrid[0:size//4, 0:size//4]
    indices = (7+3*np.sin(xx/8)+3*np.cos(yy/13)+2*np.sin((xx+yy)/3)).astype('<i4').clip(0, 15)
    append(indices.tobytes())
    minimapptr = append(b''.join(bc1_color((89, 99, 56))*(r//4)**2 for r in (1024,512,256,128,64,32,16,8,4)))
    metalptr = append(bytes((size//2)**2))
    featureptr = append(struct.pack('<2i', 0, 0))
    struct.pack_into('<16s7i2f7i', data, 0, b'spring map file\0', 1, 732197, size, size, 8, 8, 32, 0, 64,
                     heightptr, typeptr, tileptr, minimapptr, metalptr, featureptr, 0)
    (folder/'pelennor.smf').write_bytes(data)
    (output/'mapinfo.lua').write_text('return '+lua({
        'name':'bfmeXbar Pelennor', 'shortname':'BXP', 'version':'0.1', 'description':'Native integration test battlefield',
        'mapfile':'maps/pelennor.smf', 'modtype':3, 'depend':['Map Helper v1'],
        'smf':{'minheight':0,'maxheight':64}, 'gravity':130, 'tidalstrength':0,
        'atmosphere':{'suncolor':[1,.95,.85], 'skycolor':[.5,.65,.8], 'fogstart':.9},
        'lighting':{'sundir':[.4,1,.3], 'grounddiffusecolor':[.8,.8,.75], 'groundambientcolor':[.4,.4,.4],
                    'unitdiffusecolor':[.9,.85,.8], 'unitambientcolor':[.5,.5,.5]},
        'teams':{'0':{'startpos':{'x':1250,'z':2048}}, '1':{'startpos':{'x':2850,'z':2048}}},
    }), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bfme', type=pathlib.Path, default=ROOT.parent/'bfme2')
    args = parser.parse_args()
    archive = BigArchive(args.bfme/'W3D.big')
    texture_archives = [BigArchive(p) for p in sorted(args.bfme.glob('Textures*.big'))]
    ini = BigArchive(args.bfme/'INI.big'); balance, missing = convert(ini)
    destination = ROOT/'runtime'/'engine'/'games'/'bfmexbar.sdd'
    shutil.copytree(ROOT/'src/legacy'/'recoil'/'game', destination, dirs_exist_ok=True)
    (destination/'LuaUI').mkdir(exist_ok=True)
    shutil.copy2(ROOT/'src/legacy'/'recoil'/'client.lua', destination/'LuaUI'/'main.lua')
    for path in ['objects3d', 'unittextures', 'animations', 'gamedata']:
        (destination/path).mkdir(exist_ok=True)
    provenance = {'install':str(args.bfme.resolve()), 'units':{}, 'meshMode':'dominant-bone rigid triangles'}
    def read(name):
        key = next(k for k in archive.entries if k.endswith('/'+name+'.w3d'))
        return archive.read_bytes(key)
    for name, (model, skl, clip, stats_key) in UNITS.items():
        bones = skeleton(read(skl)); groups = meshes(read(model), bones)
        regions = make_atlas(groups, texture_archives, destination/'unittextures', name)
        s3o(destination/'objects3d'/(name+'.s3o'), groups, bones, name, regions, 1)
        animations = {state:animation(read(clip+'_'+suffix), bones) for state, suffix in [('idle','idla'),('run','runa'),('attack','atka')]}
        (destination/'animations'/(name+'.lua')).write_text('return '+lua(animations), encoding='utf-8')
        provenance['units'][name] = {'model':model, 'skeleton':skl, 'bones':len(bones),
            'triangles':sum(len(g['vertices'])//3 for g in groups), 'textures':list(regions),
            'clips':{state:len(a['frames']) for state,a in animations.items()}, 'balance':balance[stats_key]}
        print(name, provenance['units'][name], flush=True)
    (destination/'gamedata'/'bfme_balance.lua').write_text('return '+lua({n:balance[s[3]] for n,s in UNITS.items()}), encoding='utf-8')
    (ROOT/'runtime'/'import-report.json').write_text(json.dumps(provenance, indent=2))
    make_map(ROOT/'runtime'/'engine'/'maps'/'bfmexbar-pelennor.sdd')
    print('Built native game:', destination)


if __name__ == '__main__':
    main()
