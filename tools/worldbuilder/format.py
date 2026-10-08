"""Lossless CkMp container with narrowly scoped BFME2 authoring operations.

GPL-3.0-only. Layouts cross-checked with OpenSAGE Data/Map (see THIRD_PARTY).
Unknown chunks stay byte-identical. This is not a replacement game renderer.
"""
from collections import Counter
from dataclasses import dataclass
import hashlib
import math
import struct

import numpy as np

from tools.bfme_host.maps import unpack


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tile_offset(x, y, cell_size):
    """Native texture cells contain four 2x2 subtiles, not row-major subtile IDs."""
    return 4 * (((y // 2) % cell_size) * cell_size + (x // 2) % cell_size) + (y % 2) * 2 + x % 2


class Reader:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def take(self, n):
        if n < 0 or self.pos + n > len(self.data):
            raise ValueError('Truncated map data')
        value = self.data[self.pos:self.pos + n]
        self.pos += n
        return value

    def get(self, fmt):
        return struct.unpack('<' + fmt, self.take(struct.calcsize('<' + fmt)))

    def string(self, wide=False):
        length, = self.get('H')
        return self.take(length * (2 if wide else 1)).decode('utf-16-le' if wide else 'cp1252')

    def finish(self):
        if self.pos != len(self.data):
            raise ValueError('Unexpected trailing data')


def string(value, wide=False):
    data = value.encode('utf-16-le' if wide else 'cp1252')
    return struct.pack('<H', len(data) // (2 if wide else 1)) + data


@dataclass
class Chunk:
    name_id: int
    version: int
    data: bytes

    def encode(self):
        return struct.pack('<IHI', self.name_id, self.version, len(self.data)) + self.data


def chunks(data, names):
    result, r = [], Reader(data)
    while r.pos < len(data):
        idx, version, size = r.get('IHI')
        if idx not in names:
            raise ValueError('Unknown chunk name index')
        result.append(Chunk(idx, version, r.take(size)))
    return result


class Map:
    def __init__(self, data):
        self.original = unpack(data)
        r = Reader(self.original)
        if r.take(4) != b'CkMp':
            raise ValueError('Expected CkMp')
        count, = r.get('I')
        if count > 100000:
            raise ValueError('Too many strings')
        self.names = {}
        for expected in range(count, 0, -1):
            length = shift = 0
            while True:
                b, = r.get('B')
                length |= (b & 127) << shift
                shift += 7
                if shift > 35:
                    raise ValueError('Invalid name length')
                if b < 128:
                    break
            name = r.take(length).decode('utf-8')
            idx, = r.get('I')
            if idx != expected:
                raise ValueError('Unexpected name index')
            self.names[idx] = name
        self.chunks = chunks(r.take(len(r.data) - r.pos), self.names)

    def encode(self):
        out = bytearray(b'CkMp' + struct.pack('<I', len(self.names)))
        for idx in range(len(self.names), 0, -1):
            name = self.names[idx].encode('utf-8')
            size = len(name)
            while size >= 128:
                out.append((size & 127) | 128)
                size >>= 7
            out.append(size)
            out.extend(name + struct.pack('<I', idx))
        return bytes(out) + b''.join(c.encode() for c in self.chunks)

    def intern(self, name):
        for idx, text in self.names.items():
            if name == text:
                return idx
        idx = len(self.names) + 1
        self.names[idx] = name
        return idx

    def chunk(self, name):
        found = [c for c in self.chunks if self.names[c.name_id] == name]
        if len(found) != 1:
            raise ValueError(f'Expected exactly one {name} chunk')
        return found[0]

    def properties(self, r):
        count, = r.get('H')
        result = []
        for _ in range(count):
            kind, = r.get('B')
            name = self.names[int.from_bytes(r.take(3), 'little')]
            if kind in (0, 1, 2):
                value, = r.get({0: 'B', 1: 'i', 2: 'f'}[kind])
            elif kind in (3, 4, 5):
                value = r.string(kind == 4)
            else:
                raise ValueError(f'Unknown property kind {kind}')
            result.append((name, kind, value))
        return result

    def encode_properties(self, properties):
        out = bytearray(struct.pack('<H', len(properties)))
        for name, kind, value in properties:
            out.append(kind)
            out.extend(self.intern(name).to_bytes(3, 'little'))
            if kind in (0, 1, 2):
                out.extend(struct.pack('<' + {0: 'B', 1: 'i', 2: 'f'}[kind], value))
            else:
                out.extend(string(value, kind == 4))
        return bytes(out)

    def objects(self):
        result = []
        for i, c in enumerate(chunks(self.chunk('ObjectsList').data, self.names)):
            if self.names[c.name_id] != 'Object' or c.version != 3:
                raise ValueError('Only BFME2 Object v3 is supported')
            r = Reader(c.data)
            x, y, z, angle, flags = r.get('4fI')
            template = r.string()
            props = self.properties(r)
            r.finish()
            result.append(dict(index=i, template=template, x=x, y=y, z=z,
                               angle=angle, flags=flags, properties=props, chunk=c))
        return result

    def append_object(self, prototype, x, y, angle, name):
        # Map object Z is a terrain-relative offset. Preserve the donor's offset.
        props = [(k, t, v) for k, t, v in prototype['properties'] if k not in ('objectName', 'uniqueID')]
        props.append(('uniqueID', 3, name))
        data = (struct.pack('<4fI', x, y, prototype['z'], angle, prototype['flags'])
                + string(prototype['template']) + self.encode_properties(props))
        self.chunk('ObjectsList').data += Chunk(self.intern('Object'), 3, data).encode()

    def heightmap(self):
        c = self.chunk('HeightMapData')
        if c.version != 5:
            raise ValueError('Only BFME2 HeightMapData v5 is editable')
        r = Reader(c.data)
        w, h, border, count = r.get('4I')
        if not 1 <= w <= 4096 or not 1 <= h <= 4096 or count > 1000:
            raise ValueError('Invalid dimensions/borders')
        borders = [r.get('2I') for _ in range(count)]
        area, = r.get('I')
        if area != w * h or w <= 2 * border or h <= 2 * border:
            raise ValueError('Invalid terrain area')
        offset = r.pos
        elevations = np.frombuffer(r.take(w * h * 2), dtype='<u2').reshape(h, w)
        r.finish()
        return dict(width=w, height=h, border=border, borders=borders, offset=offset,
                    elevations=elevations)

    def blend(self):
        c, terrain = self.chunk('BlendTileData'), self.heightmap()
        if c.version != 18:
            raise ValueError('Only BFME2 BlendTileData v18 is editable')
        w, h = terrain['width'], terrain['height']
        area = w * h
        r = Reader(c.data)
        if r.get('I')[0] != area:
            raise ValueError('Blend/height dimensions disagree')
        arrays, offsets = {}, {}
        for name, dtype in [('tiles', '<u2'), ('blends', '<u4'), ('three_way', '<u4'), ('cliffs', '<u4')]:
            offsets[name] = r.pos
            arrays[name] = np.frombuffer(r.take(area * np.dtype(dtype).itemsize), dtype=dtype).reshape(h, w)
        for name in ['impassable', 'impassable_players', 'passage_widths', 'taintable', 'extra_passable', 'flammability', 'visible']:
            offsets[name] = r.pos
            if name == 'flammability':
                arrays[name] = np.frombuffer(r.take(area), dtype='u1').reshape(h, w)
            else:
                packed = np.frombuffer(r.take(((w + 7) // 8) * h), dtype='u1').reshape(h, -1)
                arrays[name] = np.unpackbits(packed, axis=1, bitorder='little')[:, :w]
        tail_offset = r.pos
        cells, blends, cliffs, texture_count = r.get('4I')
        if texture_count > 4096:
            raise ValueError('Invalid texture table')
        textures, tile_start = [], 0
        for _ in range(texture_count):
            start, count, size, magic = r.get('4I')
            if size * size != count or magic != 0 or size == 0:
                raise ValueError('Invalid texture descriptor')
            name = r.string()
            textures.append(dict(name=name, cell_start=start, cell_size=size,
                                 tile_start=tile_start, tile_count=4 * count))
            tile_start += 4 * count
        if arrays['tiles'].max() >= tile_start:
            raise ValueError('Tile index outside texture palette')
        if arrays['blends'].max() >= max(blends, 1) or arrays['three_way'].max() >= max(blends, 1):
            raise ValueError('Blend index outside palette')
        if arrays['cliffs'].max() >= max(cliffs, 1):
            raise ValueError('Cliff index outside palette')
        return dict(arrays=arrays, offsets=offsets, textures=textures, tail_offset=tail_offset)

    def report(self):
        t, b, objects = self.heightmap(), self.blend(), self.objects()
        heights = t['elevations'] * 0.0390625
        pw, ph = t['width'] - 2 * t['border'], t['height'] - 2 * t['border']
        r = Reader(self.chunk('WorldInfo').data)
        world = {k: v for k, _, v in self.properties(r)}
        r.finish()
        warnings = []
        if max(pw, ph) > 600:
            warnings.append('Over 600 tiles: editor/engine size support must be tested; not certified by this tool.')
        if any(not all(math.isfinite(o[k]) for k in ('x', 'y', 'z', 'angle')) for o in objects):
            raise ValueError('Non-finite object coordinate')
        names = [v for o in objects for k, _, v in o['properties'] if k == 'uniqueID' and v]
        duplicates = [k for k, v in Counter(names).items() if v > 1]
        if duplicates:
            warnings.append(f'Duplicate object names: {duplicates[:10]}')
        return dict(sha256=sha(self.encode()), raw_roundtrip_exact=self.encode() == self.original,
                    dimensions=dict(samples=[t['width'], t['height']], border=t['border'],
                                    playable_tiles=[pw, ph], playable_area_tiles=pw * ph,
                                    world_extent=[pw * 10, ph * 10], borders=t['borders']),
                    height_range=[float(heights.min()), float(heights.max())],
                    objects=len(objects), templates=dict(Counter(o['template'] for o in objects).most_common()),
                    textures=b['textures'], world=world, warnings=warnings,
                    chunks=[dict(name=self.names[c.name_id], version=c.version, size=len(c.data), sha256=sha(c.data)) for c in self.chunks])


def differences(before, after):
    a, b = before.report(), after.report()
    changed = []
    for i in range(max(len(a['chunks']), len(b['chunks']))):
        left = a['chunks'][i] if i < len(a['chunks']) else None
        right = b['chunks'][i] if i < len(b['chunks']) else None
        if left != right:
            changed.append((right or left)['name'])
    return dict(before_sha256=a['sha256'], after_sha256=b['sha256'],
                objects_added=b['objects'] - a['objects'],
                dimensions_before=a['dimensions'], dimensions_after=b['dimensions'],
                changed_chunks=changed,
                name_table_changed=before.names != after.names,
                warnings=b['warnings'])
