"""Read-only structural dissection of native BFME2 maps.

Run: python -m bfmexbar.mapkit.analyze FILE.map --out analysis.json
Layouts cross-checked with OpenSAGE; unresolved payloads are explicitly reported.
"""

from bfmexbar.paths import ROOT
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from bfmexbar.formats.map import Map, Reader, chunks, sha


def count(r):
    n, = r.get('I')
    if n > 100000:
        raise ValueError('Unreasonable record count')
    return n


def props(m, r):
    return {k: v for k, _, v in m.properties(r)}


RECORD_VERSIONS = {'Teams': 1, 'SidesList': (5, 6), 'BuildLists': 1, 'NamedCameras': 2,
                   'WaypointsList': 1, 'TriggerAreas': 1, 'StandingWaterAreas': 2,
                   'RiverAreas': (1, 2), 'StandingWaveAreas': (1, 2), 'EnvironmentData': (2, 3),
                   'PostEffectsChunk': 1, 'GlobalLighting': tuple(range(1, 9)),
                   'CameraAnimationList': (1, 3), 'SkyboxSettings': 1, 'PolygonTriggers': (4, 5),
                   'CastleTemplates': (1, 2, 3, 4, 5)}


def fourcc(r, allowed):
    value = r.take(4)[::-1].decode('ascii')
    if value not in allowed:
        raise ValueError(f'Unsupported camera code {value!r}')
    return value


def camera_frames(r, kind):
    frames = []
    for _ in range(count(r)):
        item = dict(frame=r.get('I')[0], interpolation=fourcc(r, ('catm','line')))
        item['position' if kind != 'target' else 'look_at'] = r.get('3f')
        if kind == 'free':item['rotation_raw'] = r.get('4f')
        if kind == 'look':item['roll'] = r.get('f')[0]
        if kind != 'target':item['fov_or_focal_parameter'] = r.get('f')[0]
        frames.append(item)
    return frames


def build_list_item(r):
    """BFME build-list entry, not the larger runtime/savegame BuildListInfo."""
    item = dict(building_name=r.string(), template=r.string(), position=r.get('3f'),
                angle=r.get('f')[0], initially_built=r.get('B')[0], rebuilds=r.get('I')[0],
                script=r.string(), health=r.get('i')[0])
    item.update(zip(('whiner', 'unsellable', 'repairable'), r.get('3B')))
    return item


def records(m, name):
    c = m.chunk(name)
    allowed = RECORD_VERSIONS.get(name, ())
    if c.version not in ((allowed,) if isinstance(allowed,int) else allowed):
        raise ValueError(f'Unsupported {name} version {c.version}')
    r = Reader(c.data)
    result = []
    if name == 'Teams':
        result = [props(m, r) for _ in range(count(r))]
    elif name == 'SidesList':
        unknown = r.get('B')[0] if c.version >= 6 else None
        for _ in range(count(r)):
            item = props(m, r)
            item['build_list'] = [build_list_item(r) for _ in range(count(r))]
            result.append(item)
        result = dict(unknown_boolean=unknown, players=result)
    elif name == 'BuildLists':
        for _ in range(count(r)):
            kind = r.get('B')[0]
            idx = int.from_bytes(r.take(3), 'little')
            result.append(dict(faction=m.names[idx], property_kind=kind,
                               items=[build_list_item(r) for _ in range(count(r))]))
    elif name == 'EnvironmentData':
        result = {}
        if c.version >= 3:
            result.update(water_max_alpha_depth=r.get('f')[0], deep_water_alpha=r.get('f')[0])
        result.update(macro_texture_stretched=r.get('B')[0], macro_texture=r.string(), cloud_texture=r.string())
    elif name == 'CastleTemplates':
        from bfmexbar.formats.castles import decode
        result = decode(r.take(len(c.data)), m.names, c.version)
    elif name == 'PostEffectsChunk':
        result = [dict(name=r.string(), blend_factor=r.get('f')[0], lookup_image=r.string())
                  for _ in range(r.get('B')[0])]
    elif name == 'GlobalLighting':
        from bfmexbar.formats.lighting import decode
        result = decode(r.take(len(c.data)), c.version)
    elif name == 'SkyboxSettings':
        result = dict(position=r.get('3f'), scale=r.get('f')[0], rotation=r.get('f')[0],
                      texture_scheme=r.string())
    elif name == 'CameraAnimationList':
        for _ in range(count(r)):
            kind = fourcc(r, ('free','look'))
            item = dict(type=kind, name=r.string(), num_frames=r.get('I')[0], start_offset=r.get('I')[0])
            item['camera_frames'] = camera_frames(r,kind)
            if kind == 'look':item['target_frames'] = camera_frames(r,'target')
            result.append(item)
    elif name == 'NamedCameras':
        for _ in range(count(r)):
            position = r.get('3f')
            label = r.string()
            values = r.get('6f')
            result.append(dict(name=label, look_at=position,
                               **dict(zip(['pitch', 'roll', 'yaw', 'zoom', 'field_of_view', 'unknown'], values))))
    elif name == 'WaypointsList':
        result = [dict(zip(['start_id', 'end_id'], r.get('2i'))) for _ in range(count(r))]
    elif name == 'PolygonTriggers':
        for _ in range(count(r)):
            item = dict(name=r.string(), layer=r.string(), id=r.get('I')[0],
                        is_water_raw=r.get('B')[0], is_river_raw=r.get('B')[0], river_start=r.get('I')[0])
            if c.version >= 5:
                for field in ('river_texture', 'noise_texture', 'alpha_edge', 'sparkle', 'bump_texture', 'sky_texture'):
                    item[field] = r.string()
                item.update(additive_raw=r.get('B')[0], river_rgb=r.get('3B'), unknown_byte=r.get('B')[0],
                            uv_speed=r.get('2f'), river_alpha=r.get('f')[0])
            item['points'] = [r.get('3i') for _ in range(count(r))]
            result.append(item)
    elif name in ('TriggerAreas', 'StandingWaterAreas', 'RiverAreas', 'StandingWaveAreas'):
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
                item['wave_parameters'] = dict(zip(
                    ('final_width','final_height','initial_width_fraction','initial_height_fraction',
                     'initial_velocity','time_to_fade','time_to_compress','second_wave_time_offset',
                     'distance_from_shore'), item['wave_parameters_raw']))
                item['texture'] = r.string()
                if c.version >= 2: item['enable_pca'] = r.get('I')[0]
            result.append(item)
    else:
        raise ValueError('No decoder for this section')
    r.finish()
    return result


def nested(m, name):
    if name == 'PlayerScriptsList':
        from bfmexbar.formats.scripts import player_scripts
        return player_scripts(m)
    expected = {'MPPositionList': 0, 'LibraryMapLists': 1, 'PlayerScriptsList': 1}
    if m.chunk(name).version != expected.get(name):
        raise ValueError(f'Unsupported {name} version {m.chunk(name).version}')
    result = []
    for c in chunks(m.chunk(name).data, m.names):
        r = Reader(c.data)
        item = dict(chunk=m.names[c.name_id], version=c.version, bytes=len(c.data))
        if item['chunk'] == 'MPPositionInfo' and c.version in (0, 1):
            item.update(human=r.get('B')[0], computer=r.get('B')[0])
            if c.version > 0:
                item['load_ai_script'] = r.get('B')[0]
            item['team'] = r.get('I')[0]
            item['side_restrictions'] = [r.string() for _ in range(count(r))] if c.version > 0 else []
        elif item['chunk'] == 'LibraryMaps' and c.version == 1:
            item['maps'] = [r.string() for _ in range(count(r))]
        else:
            item['payload_decoded'] = False
            r.take(len(c.data))
        r.finish()
        result.append(item)
    return result


def blend_details(m):
    from bfmexbar.formats.terrain import terrain_records

    b = m.blend(inspection=True)
    tail = terrain_records(m, b)
    blends, cliffs = tail['blends'], tail['cliffs']
    tile_count = sum(t['tile_count'] for t in b['textures'])
    issues = Counter(b['inspection_issues'])
    for record in blends:
        if record['direction'] is None: issues['unrecognized_blend_direction'] += 1
        if record['unknown_flag_bits']: issues['unknown_blend_flag_bits'] += 1
        if record['long_diagonal'] not in (0, 1): issues['nonboolean_long_diagonal'] += 1
        if record['marker'] != 0x7ada0000: issues['unexpected_blend_marker'] += 1
        if not -1 <= record['custom_edge_class'] < len(tail['edge_textures']):
            issues['custom_edge_outside_table'] += 1
    for record in cliffs:
        if record['flip'] not in (0, 1) or record['mutant'] not in (0, 1):
            issues['nonboolean_cliff_flags'] += 1
    for name, records in [('blend', blends), ('cliff', cliffs)]:
        issues[f'{name}_tile_outside_palette'] = sum(r['tile'] >= tile_count for r in records)
    return dict(texture_cells=tail['texture_cells'], textures=tail['textures'],
                blend_records=len(blends), cliff_mappings=len(cliffs),
                declared_blend_count=tail['declared_blend_count'],
                declared_cliff_count=tail['declared_cliff_count'],
                edge_texture_cells=tail['edge_texture_cells'], edge_textures=tail['edge_textures'],
                tail_fully_consumed=True, cliff_mapping_offset=tail['cliff_mapping_offset'],
                interpretation='Generals source names; BFME2 v18 layout cross-checked on retail maps',
                blend_example=blends[:1], cliff_example=cliffs[:1],
                blend_directions=dict(Counter(r['direction'] or r['direction_hex'] for r in blends)),
                blend_flags=dict(Counter(str(r['flags']) for r in blends)),
                long_diagonal_values=dict(Counter(str(r['long_diagonal']) for r in blends)),
                custom_edge_classes=dict(Counter(str(r['custom_edge_class']) for r in blends)),
                blend_markers=dict(Counter(hex(r['marker']) for r in blends)),
                cliff_flags=dict(Counter(f"{r['flip']},{r['mutant']}" for r in cliffs)),
                record_issues={k: v for k, v in issues.items() if v},
                arrays=[dict(name=k, shape=list(v.shape), offset=b['offsets'][k],
                             minimum=int(v.min()), maximum=int(v.max()), nonzero=int(np.count_nonzero(v)))
                        for k, v in b['arrays'].items()])


def analyze(data, source=''):
    m = Map(data)
    report = m.report(inspection=True)
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
                 'StandingWaterAreas', 'RiverAreas', 'StandingWaveAreas', 'EnvironmentData', 'PostEffectsChunk',
                 'GlobalLighting', 'CameraAnimationList', 'CastleTemplates', 'SkyboxSettings', 'PolygonTriggers',
                 'MPPositionList', 'LibraryMapLists', 'PlayerScriptsList']:
        if name in ('CastleTemplates', 'SkyboxSettings', 'PolygonTriggers') and not any(
                m.names[c.name_id] == name for c in m.chunks):
            continue
        try:
            report['decoded_sections'][name] = nested(m, name) if name in ('MPPositionList', 'LibraryMapLists', 'PlayerScriptsList') else records(m, name)
        except (ValueError, KeyError) as error:
            report['unresolved_sections'][name] = str(error)
    report['blend_details'] = blend_details(m)
    objects = m.objects()
    report['waypoints'] = [dict(position=[o['x'], o['y'], o['z']], properties={k: v for k, _, v in o['properties']})
                           for o in objects if o['template'] == '*Waypoints/Waypoint']
    report['object_flags'] = dict(Counter(str(o['flags']) for o in objects))
    from bfmexbar.mapkit.roads import inspect as inspect_roads
    report['roads'] = inspect_roads(objects)
    report['object_layers'] = dict(Counter(v for o in objects for k, _, v in o['properties'] if k == 'objectLayer'))
    report['object_example'] = {k: v for k, v in objects[0].items() if k != 'chunk'} if objects else None
    report['not_semantically_decoded'] = ['Script opcode meanings, argument constraints and execution behavior', 'Build-list runtime behavior and whiner flag',
                                         'Lighting third array, flag, vector and final-value semantics', 'Camera animation interpolation and focal-parameter semantics',
                                         'BFME2-specific terrain rendering behavior and camera fields']
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
