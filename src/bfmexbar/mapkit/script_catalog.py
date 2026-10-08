"""Extract BFME2 script signatures from a user-supplied Open-BFME-2 checkout.

No C++ is executed. Results are structural source evidence, not proof that an
action is usable in every game mode. See docs/mapping/scripts/README.md for provenance.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import copy
from importlib.resources import files


DIRECTORY = Path('Code/GameEngine/Source/GameLogic/ScriptEngine')
TOKEN = re.compile(r'curTemplate\s*=\s*&m_(action|condition)Templates\[(\d+)\]\s*;'
                   r'|curTemplate->(m_internalName|m_numParameters|m_parameters|m_targetOnly00)'
                   r'(?:\[(\d+)\])?\s*=\s*("(?:[^"\\]|\\.)*"|-?\d+)\s*;')


def load_catalog(path=None):
    """Load the bundled 1.06 signatures, or an explicitly selected local audit."""
    source = Path(path) if path is not None else files('bfmexbar.mapkit').joinpath('data/bfme2-1.06-scripts.json')
    return json.loads(source.read_text(encoding='utf-8'))


def extract(text, kind, slots):
    # Remove comments without eating // or /* inside C++ string literals.
    text = re.sub(r'"(?:[^"\\]|\\.)*"|//[^\n]*|/\*.*?\*/',
                  lambda m: m[0] if m[0].startswith('"') else '', text, flags=re.S)
    remainder = TOKEN.sub('', text)
    if re.search(r'curTemplate->(?:m_internalName|m_numParameters|m_parameters|m_targetOnly00)(?:\[[^]]*\])?\s*=', remainder):
        raise ValueError('Unsupported relevant C++ assignment; catalogue extraction must be updated')
    records = {}
    current = None
    for match in TOKEN.finditer(text):
        table, index, field, parameter, value = match.groups()
        if table:
            if table != kind:
                current = None
                continue
            index = int(index)
            if not 0 <= index < slots:
                raise ValueError('Template index outside declared table')
            current = records.setdefault(index, dict(opcode=index, parameters={}))
        elif current is None:
            continue
        elif field == 'm_internalName':
            current['name'] = json.loads(value)
        elif field == 'm_parameters':
            current['parameters'][int(parameter)] = int(value)
        elif field == 'm_numParameters':
            current['count'] = int(value)
        else:
            current['target_only_00_raw'] = int(value)
    result = []
    for index, record in sorted(records.items()):
        if 'name' not in record:
            continue  # Selected holes are present in the condition initializer.
        size = record.get('count')
        if size is not None and not 0 <= size <= 12:
            raise ValueError(f'Invalid argument count at {kind} {index}')
        record['argument_types'] = None if size is None else [record['parameters'].get(i) for i in range(size)]
        record['unresolved_parameters'] = None if size is None else [i for i in range(size) if i not in record['parameters']]
        del record['parameters']; record.pop('count', None)
        result.append(record)
    if not result:
        raise ValueError('No template records found')
    return dict(slots=slots, named=len(result),
                holes=[i for i in range(slots) if i not in {r['opcode'] for r in result}],
                templates=result)


def catalogue(root):
    result = dict(schema=1, game='BFME2 1.06', evidence='Open-BFME-2 source declarations',
                  behavior_verified=False, sources=[])
    texts = []
    for kind in ('action', 'condition'):
        path = DIRECTORY / f'ScriptEngine_init{kind.title()}Templates.cpp'
        raw = (Path(root) / path).read_bytes()
        texts.append(raw.decode('utf-8-sig'))
        result['sources'].append(dict(path=path.as_posix(), sha256=hashlib.sha256(raw).hexdigest()))
    # Execution order matters: action initialization also writes two conditions.
    for kind, slots in (('action', 599), ('condition', 202)):
        result[kind] = extract('\n'.join(texts), kind, slots)
    return result


def compare(catalog, audit):
    mismatches = []
    for signature in audit['signatures']:
        kind = 'condition' if signature['chunk'] == 'Condition' else 'action'
        table = {r['opcode']: r for r in catalog[kind]['templates']}
        expected = table.get(signature['opcode_raw'])
        if expected is None or expected['name'] != signature['internal_name'] or expected['argument_types'] != list(signature['argument_types']):
            candidates = [r for r in catalog[kind]['templates'] if r['name'] == signature['internal_name']]
            matching = [r for r in candidates if r['argument_types'] == list(signature['argument_types'])]
            status = ('same_name_and_signature_at_different_id' if len(matching) == 1 else
                      'ambiguous_name' if len(candidates) > 1 else
                      'argument_migration_needed' if candidates else 'name_not_in_current_catalog')
            mismatches.append(dict(stored=signature, template=expected,
                                   classification=status, name_candidates=candidates))
    return dict(observed_signatures=len(audit['signatures']), mismatches=mismatches,
                note='Differences may be legacy migration cases; do not rewrite automatically')


def reconcile(catalog, snapshot):
    result = copy.deepcopy(catalog)
    resolved = []
    if snapshot.get('evidence') != 'Live BFME2 1.06 template memory':
        raise ValueError('Expected a native BFME2 template snapshot')
    for kind in ('action', 'condition'):
        live = snapshot[kind]
        if len(live) != catalog[kind]['slots'] or [r['opcode'] for r in live] != list(range(len(live))):
            raise ValueError('Incomplete or reordered native template table')
        source = {r['opcode']: r for r in result[kind]['templates']}
        if {r['opcode'] for r in live if r['name']} != set(source):
            raise ValueError('Source and native template names cover different slots')
        for record in live:
            if not record['name']:
                continue
            entry = source[record['opcode']]
            if entry['name'] != record['name']:
                raise ValueError('Source and native template names disagree')
            old, new = entry['argument_types'], record['argument_types']
            if len(new) > 12 or any(not isinstance(t, int) or t < 0 for t in new):
                raise ValueError('Invalid native parameter signature')
            if old is not None and (len(old) != len(new) or any(a is not None and a != b for a, b in zip(old, new))):
                raise ValueError('Explicit source signature disagrees with native table')
            if old != new:
                resolved.append(dict(kind=kind, opcode=entry['opcode'], name=entry['name'],
                                     source_types=old, native_types=new))
            entry['argument_types'] = new
            entry['unresolved_parameters'] = []
    result['native_reconciliation'] = dict(resolved_defaults=resolved,
        snapshot_sha256=hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest(),
        semantics='Signature shape verified in memory; action behavior not established by table reads')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--audit', type=Path)
    parser.add_argument('--native', type=Path, help='Reconcile a script-check native-templates.json snapshot')
    args = parser.parse_args()
    # Keep generated research outside the source checkout.
    if args.out.resolve().is_relative_to(args.source.resolve()):
        parser.error('Output must be outside the source checkout')
    result = catalogue(args.source)
    if args.native:
        result = reconcile(result, json.loads(args.native.read_text()))
    if args.audit:
        result['comparison'] = compare(result, json.loads(args.audit.read_text()))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(action_templates=result['action']['named'],
                          condition_templates=result['condition']['named'],
                          action_holes=result['action']['holes'], condition_holes=result['condition']['holes'],
                          mismatches=len(result.get('comparison', {}).get('mismatches', [])))))


if __name__ == '__main__':
    main()
