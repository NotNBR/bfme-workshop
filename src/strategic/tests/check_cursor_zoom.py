"""Run cursor anchoring against real BFME2 cameras (requires prepared runtime).

python src/strategic/tests/check_cursor_zoom.py
The exported entry point arms the same anchor as the native wheel hook, without
moving the desktop cursor. Tests both projections, reversals and HUD rejection.
"""
from pathlib import Path
import json
import struct
import sys
import pefile

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path.insert(0, str(ROOT / 'src'))
from host import launch
from strategic.inject import read_state


def main():
    manifest = json.loads((ROOT/'local/runtime/bfme-host/manifest.json').read_text())
    sys.path.insert(0, manifest['referenceTools'])
    import game_smoke as smoke
    with pefile.PE(str(ROOT/'local/runtime/bfme-host/extension/strategic.dll')) as pe:
        exports = {e.name.decode(): e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name}
    original = smoke.skirmish_tick
    results = []
    cases = [(1050, 360, 4800), (480, 300, 300), (1100, 520, 1800),
             (600, 360, 4800), (900, 400, 300), (100, 1100, 1800)]

    def factory(args, samples, mode):
        args.seconds = 100
        args.timeout = 300
        base_tick = original(args, samples, mode)
        stage, since, initialized = 0, 0., False

        def request(game, point, height):
            def call(g, tid, ctx):
                view = g.u32(g.base+0x9FEA3C)
                module = g.res['strategic_state_address']-exports['bfxState']
                calls = []
                if point:
                    calls.append({'call': module+exports['bfxZoomBegin'], 'ecx': 0, 'args': list(point)})
                calls.append({'call': g.base+0x8D2B8, 'ecx': view,
                              'args': [struct.unpack('<I', struct.pack('<f', height))[0]]})
                def remember(g, values):
                    if point:
                        g.res['cursor_zoom_initial_anchor'] = struct.unpack('<3f', g.read(module+exports['bfxCursorZoom']+24,12))
                return {'calls': calls, 'done': remember}
            game.arm('GameEngine::update', call)

        def tick(game):
            nonlocal stage, since, initialized
            result = base_tick(game)
            frame, current = game.logic()
            if current != mode or frame is None or frame < 20:
                return result
            if not initialized:
                request(game, None, 300)
                initialized, since = True, game.seconds()
                return result
            if game.seconds()-since < 10:
                return result
            module = game.res['strategic_state_address']-exports['bfxState']
            values = struct.unpack('<4I2i5f', game.read(module+exports['bfxCursorZoom'], 44))
            if stage:
                case = cases[stage-1]
                results.append(dict(cursor=case[:2], height=case[2], active=values[0],
                                    events=values[1], corrections=values[2], rejected=values[3],
                                    anchor=values[6:9], error=values[9], max_error=values[10],
                                    initial_anchor=game.res.get('cursor_zoom_initial_anchor'),
                                    camera=read_state(game)))
                print(json.dumps({'cursor_case':stage,'events':values[1],
                                  'max_pixel_error':values[10]}),flush=True)
            if stage == len(cases):
                game.res['cursor_zoom_cases'] = results
                return 'done'
            x, y, height = cases[stage]
            request(game, (x, y), height)
            stage += 1
            since = game.seconds()
            return result
        return tick

    smoke.skirmish_tick = factory
    sys.argv = ['cursor-zoom-check', '--test', '--strategic', '--camera-trace',
                '--map', r'maps\map mp bfmexbar eight kingdoms.map']
    status = launch.main()
    failures = []
    if status: failures.append('native skirmish failed')
    if len(results) != len(cases): failures.append('incomplete cases')
    for index, case in enumerate(results):
        if case['camera']['faults']: failures.append(f'case {index}: native fault')
        if index < len(cases)-1:
            if case['active']: failures.append(f'case {index}: anchor did not release after zoom settled')
            if case['events'] != index+1 or not case['corrections']:
                failures.append(f'case {index}: anchor not applied')
            if case['max_error'] > 1: failures.append(f'case {index}: more than one pixel drift')
            if max(abs(a-b) for a,b in zip(case['anchor'],case['initial_anchor'])) > .05:
                failures.append(f'case {index}: terrain anchor moved')
            if abs(case['camera']['height']-case['height']) > 1:
                failures.append(f'case {index}: requested zoom height not reached')
        elif case['events'] != len(cases)-1 or not case['rejected'] or case['active']:
            failures.append('HUD wheel anchor was not rejected')
    report = dict(outcome='fail' if failures else 'pass', failures=failures, cases=results)
    output = ROOT/'local/runtime/bfme-host/verification/cursor-zoom-regression.json'
    output.write_text(json.dumps(report, indent=2))
    print(json.dumps(dict(outcome=report['outcome'], failures=failures)))
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
