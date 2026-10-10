"""Native render-target evidence for the strategic overlay in a prepared battle."""
import json
import struct

from PIL import Image

from common.paths import ROOT
from strategic.inject import read_state

OUT = ROOT / 'local/artifacts/strategic/unit-areas/native'
SHOTS = [('northwest-armies', 2880, 9820, 6000),
         ('eastern-field', 7970, 7920, 6000),
         ('western-field', 3700, 4300, 6000),
         ('whole-battle', 5900, 6700, 18000)]


def register(smoke):
    original = smoke.skirmish_tick
    OUT.mkdir(parents=True, exist_ok=True)

    def factory(args, samples, mode):
        args.seconds = 120
        base = original(args, samples, mode)
        stage = 0
        ready = 0
        pending = False

        def tick(game):
            nonlocal stage, ready, pending
            result = base(game)
            frame, current = game.logic()
            if current != mode or frame is None or game.res.get('kingdoms_battle', {}).get('stage') != 2:
                return result
            if stage == len(SHOTS):
                return 'done' if frame >= 150 else result
            name, x, y, height = SHOTS[stage]
            if pending:
                request, status, w, h, pitch, pixels = struct.unpack('<6I', game.read(game.res['capture_address'], 24))
                if request:
                    return result
                if status or not pixels or not (0 < w <= 8192 and 0 < h <= 8192 and w*4 <= pitch <= w*4+65536):
                    raise RuntimeError('Invalid native overlay capture')
                picture = Image.frombytes('RGB', (w, h), game.read(pixels, pitch*h), 'raw', 'BGRX', pitch, 1)
                path = OUT / (name + '.png')
                picture.save(path)
                state = read_state(game)
                state['overlay'] = dict(zip(('version','candidates','groups','merged','walls','dropped','vertices',
                    'peakMerged','peakGroups','fortress','production','economy','defense','objective','gates','areas','heroes','soldiers'),
                    struct.unpack('<18I', game.read(game.res['overlay_address'], 72))))
                game.res.setdefault('symbol_shots', []).append(dict(name=name, frame=frame, path=str(path), state=state))
                print('Overlay capture: ' + name, flush=True)
                stage += 1
                pending = False
                ready = 0
                return result
            if not ready:
                if game.va('GameEngine::update') in game.bps:
                    return result
                def move(g, tid, ctx):
                    view = g.u32(g.base + 0x9FEA3C)
                    # Reuse the game's own focus position storage for the call.
                    g.write(view + 0xC, struct.pack('<3f', x, y, 160))
                    return {'calls': [
                        {'call':g.base+0x8D55D,'ecx':view,'args':[view+0xC]},
                        {'call':g.base+0x8D2B8,'ecx':view,'args':[struct.unpack('<I',struct.pack('<f',height))[0]]}]}
                game.arm('GameEngine::update', move)
                ready = frame + 24
            elif frame >= ready:
                game.write(game.res['capture_address'], struct.pack('<I', 1))
                pending = True
            return result
        return tick
    smoke.skirmish_tick = factory


def validate(output):
    report = json.loads((output / 'skirmish_retail.json').read_text())
    shots = report['run'].get('symbol_shots', [])
    failures = []
    if report['outcome'] not in ('pass', 'blank-window'):
        failures.append(report['outcome'])
    if [s['name'] for s in shots] != [s[0] for s in SHOTS]:
        failures.append('missing native overlay captures')
    if not any(s['state']['overlay']['merged'] > 0 for s in shots):
        failures.append('no connected unit area captured')
    if any(s['state']['faults'] or s['state']['lastError'] or s['state']['overlay']['dropped'] for s in shots):
        failures.append('native fault, drawing error or capacity overflow')
    if not any(s['state']['buildings'] for s in shots):
        failures.append('missing legacy building markers')
    if not any(s['state']['overlay']['areas'] and s['state']['overlay']['heroes'] for s in shots):
        failures.append('missing unit areas or hero stars')
    if report.get('profile_touched'):
        failures.append('original profile changed')
    result = dict(outcome='fail' if failures else 'pass', failures=failures, shots=shots)
    (OUT / 'validation.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(dict(outcome=result['outcome'], failures=failures)))
    return int(bool(failures))
