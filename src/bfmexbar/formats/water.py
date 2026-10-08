"""Original BFME2 StandingWaterAreas v2 authoring with explicit asset references."""

import math
import struct

from bfmexbar.formats.map import string


def standing_water(areas):
    if len(areas)>100000: raise ValueError('Too many water areas')
    out=bytearray(struct.pack('<I',len(areas)))
    ids=set();names=set()
    for area in areas:
        if area['id'] in ids or area['name'] in names: raise ValueError('Duplicate water ID or name')
        ids.add(area['id']);names.add(area['name'])
        points=area['points']
        if not 3<=len(points)<=100000: raise ValueError('Water polygon needs 3..100000 points')
        if any(len(p)!=2 or not all(math.isfinite(v) for v in p) for p in points):
            raise ValueError('Water coordinates must be finite XY pairs')
        signed_area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))
        if abs(signed_area)<1e-6: raise ValueError('Degenerate water polygon')
        if not math.isfinite(area['uv_speed']): raise ValueError('Nonfinite water UV speed')
        if area['additive'] not in (0,1): raise ValueError('Additive flag must be boolean')
        out.extend(struct.pack('<I',area['id'])+string(area['name'])+string(area['layer']))
        out.extend(struct.pack('<fB',area['uv_speed'],area['additive']))
        out.extend(string(area['bump_texture'])+string(area['sky_texture']))
        out.extend(struct.pack('<I',len(points)))
        for p in points:out.extend(struct.pack('<2f',*p))
        out.extend(struct.pack('<I',area['water_height']))
        out.extend(string(area['shader'])+string(area['depth_colors']))
    return bytes(out)
