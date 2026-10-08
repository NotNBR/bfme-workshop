"""Observe script-created objects; never create them from the test harness."""

import json
from pathlib import Path
import struct
import shutil


def native_string(game, pointer):
    if not pointer:
        return ''
    length = struct.unpack_from('<H', game.read(pointer, 8), 4)[0]
    if length > 4096:
        raise ValueError('Native string exceeds observation bound')
    return game.read(pointer + 8, length).decode('cp1252') if length else ''


def template_snapshot(game):
    engine = game.u32(game.base + 0x9FE16C)
    if not engine:
        raise ValueError('Missing native script engine')
    result = dict(evidence='Live BFME2 1.06 template memory', action=[], condition=[])
    for kind, count, offset in (('action', 599, 0x20), ('condition', 202, 0x12BA0)):
        data = game.read(engine + offset, count * 128)
        for index in range(count):
            start = index * 128
            name = native_string(game, struct.unpack_from('<I', data, start + 0x0C)[0])
            number = struct.unpack_from('<i', data, start + 0x48)[0]
            if not 0 <= number <= 12:
                raise ValueError('Invalid native template parameter count')
            result[kind].append(dict(opcode=index, name=name,
                argument_types=list(struct.unpack_from('<' + 'i' * number, data, start + 0x4C))))
    return result


def preflight(mod, map_name, proof_path):
    from bfmexbar.capture.screenshots import resolve_map
    from bfmexbar.formats.map import sha
    proof_path = Path(proof_path)
    proof = json.loads(proof_path.read_text())
    source, _ = resolve_map(mod, map_name)
    if proof.get('schema') != 1 or source.stem != proof['map'] or sha(source.read_bytes()) != proof['map_sha256']:
        raise ValueError('Script proof does not match the installed map')
    if (proof_path.parent / 'native-validation.json').exists():
        raise ValueError('Existing native evidence: use a new run directory')
    if not proof['expected'] or set(proof['expected']) & set(proof['forbidden']):
        raise ValueError('Invalid marker expectations')
    return source


def named_objects(game):
    logic = game.u32(game.base + 0x9FE78C)
    obj = game.u32(logic + 0xAC)
    names = {}; seen = set()
    while obj and obj not in seen and len(seen) < 30000:
        seen.add(obj)
        data = game.read(obj, 0x90)
        pointer = struct.unpack_from('<I', data, 0x88)[0]
        if pointer:
            name = native_string(game, pointer)
            if name.startswith('LAB_'):
                names.setdefault(name, []).append(dict(object=obj, position=struct.unpack_from('<3f', data, 0x38)))
        obj = struct.unpack_from('<I', data, 0x8C)[0]
    if obj:
        raise ValueError('Object list cycle or observation limit reached')
    return names


def register(smoke, proof_path):
    proof = json.loads(Path(proof_path).read_text())
    original = smoke.skirmish_tick
    def factory(args, samples, mode):
        args.seconds = proof.get('duration_seconds', 40)
        basic = original(args, samples, mode)
        last = -1
        def tick(game):
            nonlocal last
            result = basic(game)
            frame, current = game.logic()
            if current != mode or frame is None or frame == last:
                return result
            last = frame
            evidence = game.res.setdefault('script_lab', dict(proof=proof, first_seen={}, first_seen_seconds={}, forbidden_seen={}, samples=[]))
            if 'native_templates' not in evidence:
                evidence['native_templates'] = template_snapshot(game)
            if 'lighting' in proof and 'native_lighting' not in evidence:
                from bfmexbar.mapkit.lighting_check import snapshot
                evidence['native_lighting'] = snapshot(game)
            names = named_objects(game)
            for name in names:
                evidence['first_seen'].setdefault(name, frame)
                evidence['first_seen_seconds'].setdefault(name, game.seconds())
                if name in proof['forbidden']:
                    evidence['forbidden_seen'].setdefault(name, frame)
            evidence['samples'].append(dict(frame=frame, seconds=game.seconds(), objects=names))
            return result
        return tick
    smoke.skirmish_tick = factory


def validate(output, proof_path, source=None):
    proof_path = Path(proof_path)
    report = json.loads((output / 'skirmish_retail.json').read_text())
    evidence = report.get('run', {}).get('script_lab', {})
    errors = []
    if report['outcome'] not in ('pass', 'blank-window'):
        errors.append(report['outcome'])
    if report.get('profile_touched'):
        errors.append('Original profile changed')
    proof = json.loads(proof_path.read_text())
    if source is not None:
        from bfmexbar.formats.map import sha
        if sha(Path(source).read_bytes()) != proof['map_sha256']:
            errors.append('Installed map changed during the native run')
    samples = evidence.get('samples', [])
    if not samples or samples[-1]['frame'] < proof['minimum_frame']:
        errors.append('Insufficient native script observation')
    for name in proof['expected']:
        matches = samples[-1]['objects'].get(name, []) if samples else []
        if len(matches) != 1:
            errors.append(f'Expected exactly one live {name}; found {len(matches)}')
    for choices in proof.get('one_of', []):
        observed = samples[-1]['objects'] if samples else {}
        if sum(len(observed.get(name, [])) for name in choices) != 1:
            errors.append(f'Expected exactly one outcome marker from {choices}')
    if evidence.get('forbidden_seen'):
        errors.append('Disabled/false-branch action unexpectedly executed')
    if 'lighting' in proof:
        from bfmexbar.mapkit.lighting_check import differences
        errors.extend(differences(proof['lighting'], evidence.get('native_lighting')))
    movement = []
    for case in proof.get('movement_cases', []):
        observed = samples[-1]['objects'] if samples else {}
        objects = observed.get(case['unit'], [])
        reachable = case['reachable_marker'] in observed
        if len(objects) != 1:
            errors.append(f"Missing movement unit {case['unit']}")
            continue
        track = [(s['frame'],s['objects'][case['unit']][0]['position'][0]) for s in samples
                 if len(s['objects'].get(case['unit'],[]))==1]
        maximum = max(x for _,x in track)
        crossings = [frame for frame,x in track if x >= case['far_bank_x']]
        # A unit can complete its move then receive another order from game AI.
        # Reachability is demonstrated by crossing, not remaining there forever.
        passed = bool(crossings) if reachable else maximum < case['near_bank_x']
        movement.append(dict(unit=case['unit'], query_reachable=reachable,
                             final_x=objects[0]['position'][0], max_x=maximum,
                             first_crossing_frame=crossings[0] if crossings else None, agrees=passed))
        if not passed: errors.append(f"Movement disagrees with path query: {case['unit']}")
    first = evidence.get('first_seen', {})
    timing = []
    for check in proof['timer_checks']:
        times = first if check['basis'] == 'frames' else evidence.get('first_seen_seconds', {})
        if check['name'] in times and proof['timer_reference'] in times:
            delta = times[check['name']] - times[proof['timer_reference']]
            timing.append(dict(**check, observed_delta=delta))
            if not check['minimum'] <= delta <= check['maximum']:
                errors.append(f"{check['name']} outside its {check['basis']} observation window")
    result = dict(outcome='fail' if errors else 'pass', errors=errors, proof=proof,
                  first_seen=first, final_sample=samples[-1] if samples else None,
                  timing=timing,
                  native_lighting=evidence.get('native_lighting'),
                  movement=movement,
                  observation='Read-only native object census; no harness-created marker objects',
                  strategic_extension_loaded=bool(report.get('run', {}).get('strategic')))
    if 'native_templates' in evidence:
        (proof_path.parent / 'native-templates.json').write_text(json.dumps(evidence['native_templates'], indent=2) + '\n')
    destination = proof_path.parent / 'native-validation.json'
    shutil.copy2(output / 'skirmish_retail.json', proof_path.parent / 'engine-report.json')
    destination.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 1 if errors else 0
