"""Exercise the native camera-height setter at normal and maximum map height."""

from common.paths import ROOT
import struct
import json


def validate(output):
    from PIL import Image, ImageStat
    report = json.loads((output / 'skirmish_retail.json').read_text())
    run = report['run']
    check = run.get('zoom_check', {})
    requested = run.get('zoom_heights_requested', [])
    image = Image.open(output / 'zoom-end.png').convert('L')
    width, height = image.size
    # Upper central world region excludes the BFME HUD and off-map margins.
    world = image.crop((int(width*.3), int(height*.15), int(width*.7), int(height*.55)))
    stats = ImageStat.Stat(world)
    visible = sum(world.histogram()[9:]) / (world.width * world.height)
    passed = (report['outcome'] == 'pass' and len(requested) == 2
              and run.get('zoom_start_height') == 300
              and check.get('height') == requested[-1]
              and check.get('clipPlanes', [0, 0])[1] > requested[-1] * 2
              and stats.mean[0] > 8 and stats.stddev[0] > 3 and visible > .2)
    result = {'outcome': 'pass' if passed else 'fail', 'requestedHeights': requested,
              'actualStartHeight': run.get('zoom_start_height'), **check,
              'worldMean': stats.mean[0], 'worldStddev': stats.stddev[0],
              'worldVisibleFraction': visible,
              'scope': 'Udun camera regression, not general large-battle performance'}
    (output / 'zoom-regression.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0 if passed else 1


def register(smoke):
    original = smoke.skirmish_tick

    def factory(args, samples, mode):
        base_tick = original(args, samples, mode)
        stage = 0

        def set_height(game, target):
            def handler(game, tid, ctx):
                view = game.u32(game.base + 0x9FEA3C)
                vtable = game.u32(view)
                setter = game.base + 0x8D2B8
                slots = struct.unpack('<160I', game.read(vtable, 160 * 4))
                if slots.count(setter) != 1:
                    raise RuntimeError('Unexpected native camera-height setter')
                game.res.setdefault('zoom_heights_requested', []).append(target)
                return {'call': setter, 'ecx': view,
                        'args': [struct.unpack('<I', struct.pack('<f', target))[0]]}
            game.arm('GameEngine::update', handler)

        def tick(game):
            nonlocal stage
            result = base_tick(game)
            frame, current_mode = game.logic()
            if current_mode != mode or not frame or frame < 20:
                return result
            view = game.u32(game.base + 0x9FEA3C)
            if not view:
                return result
            if stage == 0:
                set_height(game, 300.0)
                stage = 1
            elif stage == 1 and frame >= 50:
                game.res['zoom_start'] = game._while_serving(
                    lambda: smoke.capture(game.pid, smoke.OUT / 'zoom-start.png'))
                game.res['zoom_start_height'] = struct.unpack('<f', game.read(view + 0x40, 4))[0]
                # Native camera settings embedded in W3DView: max height +8.
                maximum = struct.unpack('<f', game.read(view + 0x24D0, 4))[0]
                if not 300 <= maximum <= 24000:
                    raise RuntimeError(f'Unexpected map camera maximum: {maximum}')
                set_height(game, maximum)
                stage = 2
            if result:
                camera = game.u32(view + 0x104)
                planes = game.read(camera + 0xEC, 8)
                game.res['zoom_check'] = {
                    'height': struct.unpack('<f', game.read(view + 0x40, 4))[0],
                    'clipPlanes': struct.unpack('<2f', planes),
                }
                game.res['zoom_end'] = game._while_serving(
                    lambda: smoke.capture(game.pid, smoke.OUT / 'zoom-end.png'))
            return result
        return tick
    smoke.skirmish_tick = factory
