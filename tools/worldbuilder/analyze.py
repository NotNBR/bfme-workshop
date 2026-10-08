"""Read-only structural dissection of native BFME2 maps.

Run: python -m tools.worldbuilder.analyze FILE.map --out analysis.json
Layouts cross-checked with OpenSAGE; unresolved payloads are explicitly reported.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from .format import Map, Reader, chunks, sha


def count(r):
    n, = r.get('I')
    if n > 100000:
        raise ValueError('Unreasonable record count')
    return n


def props(m, r):
    return {k: v for k, _, v in m.properties(r)}


def records(m, name):
    c = m.chunk(name)
    r = Reader(c.data)
    result = []
    if name == 'Teams':
        result = [props(m, r) for _ in range(count(r))]
    elif name == 'SidesList':
        if c.version != 6:
            raise ValueError('Only SidesList v6 decoded here')
        unknown = r.get('B')[0]
        for _ in range(count(r)):
            item = props(m, r)
            n = count(r)
            if n:
                raise ValueError('Embedded nonempty player build list needs further decoding')
            result.append(item)
        result = dict(unknown_boolean=unknown, players=result)
    elif name == 'BuildLists':
        for _ in range(count(r)):
            kind = r.get('B')[0]
            idx = int.from_bytes(r.take(3), 'little')
            n = count(r)
            if n:
                raise ValueError('Nonempty faction build list needs further decoding')
            result.append(dict(faction=m.names[idx], property_kind=kind, items=[]))
    elif name == 'NamedCameras':
        for _ in range(count(r)):
            position = r.get('3f')
            label = r.string()
            values = r.get('6f')
            result.append(dict(name=label, look_at=position,
                               **dict(zip(['pitch', 'roll', 'yaw', 'zoom', 'field_of_view', 'unknown'], values))))
    elif name == 'WaypointsList':
        result = [dict(zip(['start_id', 'end_id'], r.get('2i'))) for _ in range(count(r))]
    elif name in ('TriggerAreas', 'StandingWaterAreas', 'RiverAreas', 'StandingWaveAreas'):
        if name != 'TriggerAreas' and c.version != 2:
            raise ValueError('Only BFME2 water v2 decoded here')
        for _ in range(count(r)):
            item = {}
            if name == 'TriggerAreas':
                item.update(name=r.string(), layer=r.string(), id=r.get('I')[0])
            else:
                item.update(id=r.get('I')[0], name=r.string(), layer=r.string(),
                            uv_speed=r.get('f')[0], additive=r.get('B')[0])
            if name == 'StandingWaterAreas':
                item.update(bump_texture=r.string(), sky_texture=r.string())
            if name == 'RiverAreas':
                item.update(texture=r.string(), noise=r.string(), alpha_edge=r.string(), sparkle=r.string(),
                            color_bytes=r.get('4B'), alpha=r.get('f')[0], water_height=r.get('I')[0], min_lod=r.string())
                item['cross_sections'] = [r.get('4f') for _ in range(count(r))]
            else:
                item['points'] = [r.get('2f') for _ in range(count(r))]
            if name == 'StandingWaterAreas':
                item.update(water_height=r.get('I')[0], shader=r.string(), depth_colors=r.string())
            if name in ('TriggerAreas', 'StandingWaveAreas'):
                item['unknown_u32'] = r.get('I')[0]
            if name == 'StandingWaveAreas':
                item['wave_parameters_raw'] = r.get('9I')
                item.update(texture=r.string(), enable_pca=r.get('I')[0])
            result.append(item)
    else:
        raise ValueError('No decoder for this section')
    r.finish()
    return result


def nested(m, name):
    result = []
    for c in chunks(m.chunk(name).data, m.names):
        r = Reader(c.data)
        item = dict(chunk=m.names[c.name_id], version=c.version, bytes=len(c.data))
        if item['chunk'] == 'MPPositionInfo':
            item.update(human=r.get('B')[0], computer=r.get('B')[0])
            if c.version > 0:
                item['load_ai_script'] = r.get('B')[0]
            item['team'] = r.get('I')[0]
            item['side_restrictions'] = [r.string() for _ in range(count(r))] if c.version > 0 else []
        elif item['chunk'] == 'LibraryMaps':
            item['maps'] = [r.string() for _ in range(count(r))]
        elif item['chunk'] == 'ScriptList' and c.version == 1:
            item['children'] = []
            for child in chunks(c.data, m.names):
                entry = dict(chunk=m.names[child.name_id], version=child.version, bytes=len(child.data))
                entry['name'] = Reader(child.data).string()
                entry['payload_decoded'] = False
                item['children'].append(entry)
            r.take(len(c.data))
        else:
            item['payload_decoded'] = False
            r.take(len(c.data))
        r.finish()
        result.append(item)
    return result


def blend_details(m):
    b = m.blend()
    r = Reader(m.chunk('BlendTileData').data)
    r.take(b['tail_offset'])
    cells, blend_count, cliff_count, texture_count = r.get('4I')
    for _ in range(texture_count):
        r.get('4I'); r.string()
    unknown1, unknown2 = r.get('2I')
    blends = []
    for _ in range(max(0, blend_count - 1)):
        tile, direction, flags, two_sided, magic1, magic2 = r.get('I4sBBII')
        blends.append(dict(tile=tile, direction_hex=direction.hex(), flags=flags, two_sided=two_sided,
                           magic1=magic1, magic2=magic2))
    cliff_start = r.pos
    for _ in range(max(0, cliff_count - 1)):
        r.get('I8fH')
    r.finish()
    return dict(texture_cells=cells, textures=texture_count, blend_records=len(blends),
                cliff_mappings=max(0, cliff_count - 1), unknown_header=[unknown1, unknown2],
                tail_fully_consumed=True, cliff_mapping_offset=cliff_start,
                blend_example=blends[:1],
                arrays=[dict(name=k, shape=list(v.shape), offset=b['offsets'][k],
                             minimum=int(v.min()), maximum=int(v.max()), nonzero=int(np.count_nonzero(v)))
                        for k, v in b['arrays'].items()])


def analyze(data, source=''):
    m = Map(data)
    report = m.report()
    report['source'] = source
    report['file_sha256'] = sha(data)
    report['file_bytes'] = len(data)
    report['container'] = data[:4].decode('ascii', errors='replace')
    report['decompressed_bytes'] = len(m.original)
    offset = len(m.original) - sum(10 + len(c.data) for c in m.chunks)
    report['name_table'] = dict(entries=len(m.names), starts_at=8, ends_at=offset)
    for info, c in zip(report['chunks'], m.chunks):
        info.update(header_offset=offset, payload_offset=offset + 10, end_offset=offset + 10 + len(c.data))
        offset += 10 + len(c.data)
    report['decoded_sections'], report['unresolved_sections'] = {}, {}
    for name in ['SidesList', 'Teams', 'BuildLists', 'NamedCameras', 'WaypointsList', 'TriggerAreas',
                 'StandingWaterAreas', 'RiverAreas', 'StandingWaveAreas', 'MPPositionList', 'LibraryMapLists', 'PlayerScriptsList']:
        try:
            report['decoded_sections'][name] = nested(m, name) if name in ('MPPositionList', 'LibraryMapLists', 'PlayerScriptsList') else records(m, name)
        except (ValueError, KeyError) as error:
            report['unresolved_sections'][name] = str(error)
    report['blend_details'] = blend_details(m)
    objects = m.objects()
    report['waypoints'] = [dict(position=[o['x'], o['y'], o['z']], properties={k: v for k, _, v in o['properties']})
                           for o in objects if o['template'] == '*Waypoints/Waypoint']
    report['object_flags'] = dict(Counter(str(o['flags']) for o in objects))
    report['object_layers'] = dict(Counter(v for o in objects for k, _, v in o['properties'] if k == 'objectLayer'))
    report['object_example'] = {k: v for k, v in objects[0].items() if k != 'chunk'} if objects else None
    report['not_semantically_decoded'] = ['Script action/condition operands', 'Nonempty build-list entries',
                                         'Lighting, post-effects and environment payloads', 'Animated camera tracks',
                                         'Unknown blend flags and camera fields']
    if m.encode() != m.original:
        raise AssertionError('Analysis failed lossless round-trip check')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('map', type=Path)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    data = args.map.read_bytes()
    report = analyze(data, str(args.map.resolve()))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    if args.map.read_bytes() != data:
        raise RuntimeError('Source changed during analysis')
    print(json.dumps(dict(report=str(args.out), chunks=len(report['chunks']), unresolved=report['unresolved_sections'], source_unchanged=True)))


if __name__ == '__main__':
    main()
