"""Build an original map that exposes script results as named native objects."""

import argparse
import json
from pathlib import Path
import struct

from PIL import Image

from common.paths import ROOT
from formats.map import Map, sha, string
from formats.scripts import player_scripts, inventory
from mapkit.blank import create, starts, add_object
from mapkit.script_writer import Writer, arg


NAME = 'map mp bfmexbar script lab'


def build(catalog=None, *, lighting_probe=False, execution_probe=False):
    m = create(128, 128, 8, title='BFME Workshop Script Lab')
    starts(m, [(200, 180), (1080, 180)])
    add_object(m, 'GondorFighter', 1100, 1100, extra=[('objectName', 3, 'LAB_Control')])
    markers = ['Init', 'CounterFlag', 'FrameTimer', 'SecondsTimer', 'FalseBranch',
               'DisabledCondition', 'OrBranch', 'AreaInside']
    for i, label in enumerate(markers):
        add_object(m, '*Waypoints/Waypoint', 260 + i % 4 * 240, 650 + i // 4 * 250,
                   extra=[('uniqueID', 3, 'WP_' + label), ('waypointName', 3, 'WP_' + label),
                          ('waypointID', 1, 100 + i), ('originalOwner', 3, '/team')])
    polygon = [(200., 580.), (400., 580.), (400., 730.), (200., 730.)]
    m.chunk('TriggerAreas').data = (struct.pack('<I', 1) + string('InitArea') + string('Tests')
        + struct.pack('<II', 1, len(polygon)) + b''.join(struct.pack('<2f', *p) for p in polygon)
        + struct.pack('<I', 0))
    w = Writer(m, catalog)
    text = lambda kind, value: arg(kind, text=value)
    integer = lambda kind, value: arg(kind, integer=value)
    def condition(name, arguments=(), **kw):
        return w.operation('condition', name, arguments, **kw)
    def action(name, arguments=(), **kw):
        return w.operation('action', name, arguments, **kw)
    def spawn(label, *, branch='action', enabled=True, waypoint=None):
        return w.operation(branch, 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT', [
            text(14, 'LAB_' + label), text(15, 'GondorFighter'),
            text(3, 'teamPlyrCivilian'), text(7, 'WP_' + (waypoint or label))], enabled=enabled)
    true = lambda: [[condition('CONDITION_TRUE')]]
    scripts = [w.script('LabInit', true(), [
        action('SET_COUNTER', [text(4, 'LabCounter'), integer(0, 7)]),
        action('SET_FLAG', [text(5, 'LabFlag'), integer(8, 1)]),
        action('SET_TIMER', [text(4, 'LabFrameTimer'), integer(0, 60)]),
        action('SET_MILLISECOND_TIMER', [text(4, 'LabSecondsTimer'), arg(1, real=2.)]),
        spawn('Init')])]
    scripts.append(w.script('LabCounterFlag', [[
        condition('COUNTER', [text(4, 'LabCounter'), integer(6, 2), integer(0, 7)]),
        condition('FLAG', [text(5, 'LabFlag'), integer(8, 1)])]], [spawn('CounterFlag')]))
    for label, timer in (('FrameTimer', 'LabFrameTimer'), ('SecondsTimer', 'LabSecondsTimer')):
        scripts.append(w.script('Lab' + label, [[condition('TIMER_EXPIRED', [text(4, timer)])]], [spawn(label)]))
    scripts.append(w.script('LabFalseBranch', [[condition('CONDITION_FALSE')]],
        [spawn('ForbiddenFalseTrue', waypoint='FalseBranch')], [
        spawn('FalseBranch', branch='false_action'),
        w.operation('false_action', 'DISABLE_SCRIPT', [text(2, 'LabFalseBranch')])]))
    scripts.append(w.script('LabFlag4D', [[condition('CONDITION_FALSE', condition_flag=1)]],
                            [spawn('ForbiddenFlag4D', waypoint='DisabledCondition')]))
    scripts.append(w.script('LabDisabledCondition', [[condition('CONDITION_FALSE', enabled=False)]],
                            [spawn('DisabledCondition')]))
    scripts.append(w.script('LabAndFalse', [[condition('CONDITION_TRUE'), condition('CONDITION_FALSE')]],
                            [spawn('ForbiddenAnd', waypoint='DisabledCondition')]))
    scripts.append(w.script('LabOrBranch', [[condition('CONDITION_FALSE')],
                                          [condition('CONDITION_TRUE')]], [spawn('OrBranch')]))
    scripts.append(w.script('LabAreaInside', [[condition('NAMED_INSIDE_AREA',
        [text(14, 'LAB_Init'), text(9, 'InitArea')], opcode=13)]], [spawn('AreaInside')]))
    scripts.append(w.script('LabDisabledAction', true(), [spawn('ForbiddenAction', enabled=False, waypoint='Init')]))
    scripts.append(w.script('LabDisabledScript', true(), [spawn('ForbiddenScript', waypoint='Init')], active=False))
    execution_expected = []
    execution_forbidden = []
    difficulty_markers = []
    if execution_probe:
        def marker(label, **settings):
            return w.script('Lab' + label, true(), [spawn(label, waypoint='Init')], **settings)
        scripts.extend([
            w.group('LabActiveGroup', [marker('GroupActive')]),
            w.group('LabOuterGroup', [w.group('LabInnerGroup', [marker('NestedActive')])]),
            w.group('LabInactiveGroup', [marker('ForbiddenInactiveGroup')], active=False),
            w.group('LabInactiveParent', [w.group('LabActiveChild', [marker('ForbiddenInactiveParent')])], active=False),
            w.group('LabActiveParent', [w.group('LabInactiveChild', [marker('ForbiddenInactiveChild')], active=False)]),
            marker('CalledSubroutine', subroutine=True),
            marker('ForbiddenUncalledSubroutine', subroutine=True),
            w.script('LabCallSubroutine', true(), [action('CALL_SUBROUTINE', [text(13, 'LabCalledSubroutine')])]),
            marker('ForbiddenAllDifficulties', easy=False, medium=False, hard=False),
        ])
        for difficulty in ('easy', 'medium', 'hard'):
            label = 'Difficulty' + difficulty.title()
            scripts.append(marker(label, **{key: key == difficulty for key in ('easy','medium','hard')}))
            difficulty_markers.append('LAB_' + label)
        execution_expected = ['LAB_GroupActive', 'LAB_NestedActive', 'LAB_CalledSubroutine']
        execution_forbidden = ['LAB_Forbidden' + label for label in ('InactiveGroup','InactiveParent',
                               'InactiveChild','UncalledSubroutine','AllDifficulties')]
    w.install(scripts, side_index=2)  # PlyrCivilian, as in retail skirmish scripts.
    data = m.encode()
    assert inventory(player_scripts(Map(data)))['payloads_decoded']
    proof = dict(schema=1, map=NAME, map_sha256=sha(data), minimum_frame=150,
                 expected=['LAB_Control'] + ['LAB_' + label for label in markers],
                 forbidden=['LAB_ForbiddenFalseTrue', 'LAB_ForbiddenAction', 'LAB_ForbiddenScript',
                            'LAB_ForbiddenFlag4D', 'LAB_ForbiddenAnd'],
                 timer_reference='LAB_Init',
                 timer_checks=[dict(name='LAB_FrameTimer', basis='frames', minimum=55, maximum=70),
                               dict(name='LAB_SecondsTimer', basis='seconds', minimum=1, maximum=4)],
                 scripts=len(scripts))
    if execution_probe:
        proof['expected'] += execution_expected
        proof['forbidden'] += execution_forbidden
        proof['one_of'] = [difficulty_markers]
        proof['execution_probe'] = 'Nested group activation, explicit subroutine call and difficulty gates'
    if lighting_probe:
        from formats.lighting import decode, encode
        value = decode(m.chunk('GlobalLighting').data, 8)
        for time, config in enumerate(value['configurations']):
            for slot, light in enumerate(config):
                i = time*9 + slot
                light['ambient'] = (.04+i*.001, .05+i*.001, .06+i*.001)
                light['diffuse'] = (.2+i*.005, .25+i*.005, .3+i*.005)
                light['direction'] = (.1+i*.01, .15+i*.01, -1.)
        value.update(overbright_value=2., chunk_flag_raw=1,
                     vector_triplets=[(.125,.25,.375),(.5,.625,.75),(.875,1.,.5)],
                     shadow_color_raw=0xFF708090, final_values=(.75,.875,1.))
        m.chunk('GlobalLighting').data = encode(value)
        proof['lighting'] = decode(m.chunk('GlobalLighting').data, 8)
        proof['map_sha256'] = sha(m.encode())
    return m, proof


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog', type=Path, help='Defaults to the bundled BFME2 1.06 catalogue')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--install', action='store_true')
    p.add_argument('--lighting-probe', action='store_true', help='Use distinct values in every lighting slot and verify native readback')
    p.add_argument('--execution-probe', action='store_true', help='Test nested group activation, subroutines and difficulty gates')
    args = p.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        p.error('Use a new or empty output directory to preserve evidence')
    from mapkit.script_catalog import load_catalog
    m, proof = build(load_catalog(args.catalog), lighting_probe=args.lighting_probe, execution_probe=args.execution_probe)
    args.out.mkdir(parents=True, exist_ok=True)
    data = m.encode()
    (args.out / (NAME + '.map')).write_bytes(data)
    (args.out / 'proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    if args.install:
        config = json.loads((ROOT / 'local/runtime/bfme-host/manifest.json').read_text())
        target = Path(config['mod']) / 'maps' / NAME
        target.mkdir(parents=True, exist_ok=True)
        path = target / (NAME + '.map')
        path.write_bytes(data)
        for suffix in ('_art.tga', '_pic.tga'):
            Image.new('RGB', (256, 256), (90, 75, 58)).save(target / (NAME + suffix))
        from mapkit.cache import cache_entry
        cache_entry(path, m, NAME, 'BFME Workshop Script Lab', 'Original script behavior tests.')
    print(json.dumps(proof))


if __name__ == '__main__':
    main()
