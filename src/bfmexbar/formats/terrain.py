"""Inspect terrain records in local BFME2/legacy maps (BlendTileData v8..18).

Retain raw values alongside source-based names; legacy semantics may differ.

See docs/worldbuilder-terrain.md for provenance and the limits of interpretation.
This module does not change or regenerate terrain data.
"""

import math

from bfmexbar.formats.map import Reader


DIRECTIONS = ('horizontal', 'vertical', 'right_diagonal', 'left_diagonal')


def terrain_records(m, blend=None):
    blend = m.blend(inspection=True) if blend is None else blend
    r = Reader(m.chunk('BlendTileData').data)
    r.take(blend['tail_offset'])
    cells, blend_count, cliff_count, texture_count = r.get('4I')
    for _ in range(texture_count):
        r.get('4I')
        r.string()
    edge_cells, edge_count = r.get('2I')
    edges = []
    for _ in range(edge_count):
        start, count, size = r.get('3I')
        edges.append(dict(cell_start=start, cell_count=count, cell_size=size, name=r.string()))

    blends = []
    for index in range(1, blend_count):
        tile, direction, flags, long_diagonal, edge, marker = r.get('I4sBBiI')
        # Do not coerce unusual direction bytes into booleans or discard flag bits.
        known_direction = all(v in (0, 1) for v in direction) and sum(direction) == 1
        blends.append(dict(index=index, tile=tile, direction_hex=direction.hex(),
                           direction=DIRECTIONS[direction.index(1)] if known_direction else None,
                           flags=flags, inverted=bool(flags & 1), force_flip=bool(flags & 2),
                           unknown_flag_bits=flags & ~3, long_diagonal=long_diagonal,
                           custom_edge_class=edge, marker=marker))

    cliff_offset = r.pos
    cliffs = []
    for index in range(1, cliff_count):
        tile, *values = r.get('I8fBB')
        uv, flip, mutant = values[:8], values[8], values[9]
        if not all(math.isfinite(v) for v in uv):
            raise ValueError(f'Non-finite cliff UV in record {index}')
        cliffs.append(dict(index=index, tile=tile,
                           uv=[uv[i:i + 2] for i in range(0, 8, 2)],
                           flip=flip, mutant=mutant))
    r.finish()
    return dict(texture_cells=cells, textures=texture_count,
                declared_blend_count=blend_count, declared_cliff_count=cliff_count,
                edge_texture_cells=edge_cells, edge_textures=edges,
                blends=blends, cliffs=cliffs, cliff_mapping_offset=cliff_offset)
