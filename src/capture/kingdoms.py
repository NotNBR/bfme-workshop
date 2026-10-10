"""Configure the native camera director from an authored showcase shot list."""
import json
import math
from pathlib import Path
import struct
import tomllib
from common.paths import ROOT

PROJECT = ROOT / 'examples/showcases/eight_kingdoms'


def resolve_shots(fronts, project=PROJECT):
    config = tomllib.loads((project / 'project.toml').read_text())
    if (config['fps'], config['capture_width'], config['capture_height']) != (30, 1600, 720):
        raise ValueError('Native director currently requires 1600x720 at 30 fps')
    entries = json.loads((project / config['shots']).read_text())
    if not 1 <= len(entries) <= 12:
        raise ValueError('Native director accepts 1..12 shots')

    def point(value):
        if isinstance(value, dict):
            base = fronts[value['front']]
            offset = value.get('offset', [0, 0])
            value = [base[0] + offset[0], base[1] + offset[1]]
        if len(value) != 2 or not all(math.isfinite(v) for v in value):
            raise ValueError('Shot positions must be two finite world coordinates')
        return value

    shots = []
    for shot in entries:
        x, y = point(shot['start']); end_x, end_y = point(shot['end'])
        span, end_span = shot['span']; elev, end_elev = shot['elevation']
        frames = shot['frames']
        if not all(math.isfinite(v) for v in (span,end_span,elev,end_elev)) or min(span,end_span) <= 0:
            raise ValueError('Shot spans must be positive and camera values finite')
        if not isinstance(frames, int) or not 1 <= frames <= 30000 or not 0 < min(elev,end_elev) <= max(elev,end_elev) <= 90:
            raise ValueError('Invalid shot duration or elevation')
        shots.append((x,y,span,elev,end_x-x,end_y-y,end_span,end_elev,frames,int(shot.get('strategic',False))))
    return shots


def start_recording(game, module, exports, plan, output):
    shots = resolve_shots(plan['fronts'])
    command = str(Path(output) / 'battle-footage.bgr0').encode('mbcs')
    if len(command) >= 2048:
        raise ValueError('Native capture path exceeds its 2048-byte ABI buffer')
    # Verified BFME2 1.06 hero-death notification wrapper; recording process only.
    notification = game.base + 0x2A1283
    expected = bytes.fromhex('d981e409000051d91c248d81e0090000506850d3bf00ff742410e8b2e6ffffc20400')
    if game.read(notification,len(expected)) != expected:
        raise RuntimeError('Unexpected hero notification function')
    if not game.write(notification,b'\xc2\x04\x00',code=True) or game.read(notification,3) != b'\xc2\x04\x00':
        raise RuntimeError('Could not disable cinematic hero notification')
    game.res['capture_hero_notifications_suppressed'] = True
    data = b''.join(struct.pack('<8f2I',x,y,span,math.radians(elev),dx,dy,end_span,
                math.radians(end_elev),frames,strategic)
                for x,y,span,elev,dx,dy,end_span,end_elev,frames,strategic in shots)
    game.write(module+exports['bfxMovieShots'],data)
    game.write(module+exports['bfxMovie'],struct.pack('<7I2048s2I',1,0,0,0,
               sum(s[-2] for s in shots),0,len(shots),command,0,0))
    game.res['kingdoms_recording'] = True
