"""Read BFME2 map scripts without applying another game's opcode enum.

Source provenance and semantic limits: docs/reference/mapping/scripts/README.md. This is a read-only
decoder; it does not rewrite scripts or apply runtime compatibility migrations.
"""

from collections import Counter

from formats.map import Reader, chunks


VERSIONS = {'ScriptList': (1,), 'ScriptGroup': (1, 2, 3), 'Script': (1, 2, 3, 4),
            'OrCondition': (1,), 'Condition': (4, 5, 6),
            'ScriptAction': (2, 3), 'ScriptActionFalse': (2, 3)}
CHILDREN = {'ScriptList': ('Script', 'ScriptGroup'),
            'ScriptGroup': ('Script', 'ScriptGroup'),
            'Script': ('OrCondition', 'ScriptAction', 'ScriptActionFalse'),
            'OrCondition': ('Condition',)}


def argument(r):
    kind = r.get('I')[0]
    if kind == 16:
        return dict(type_id=kind, position=r.get('3f'))
    # These are three stored fields, not a union: do not discard "unused" values.
    return dict(type_id=kind, int_value=r.get('i')[0],
                float_value=r.get('f')[0], string_value=r.string())


def node(m, chunk, depth=0):
    name = m.names[chunk.name_id]
    result = dict(chunk=name, version=chunk.version, bytes=len(chunk.data),
                  payload_decoded=False)
    try:
        if depth > 64:
            raise ValueError('Script nesting exceeds tool limit of 64')
        if chunk.version not in VERSIONS.get(name, ()):
            raise ValueError(f'Unsupported {name} version {chunk.version}')
        r = Reader(chunk.data)
        if name == 'ScriptGroup':
            result.update(name=r.string(), active_raw=r.get('B')[0],
                          subroutine_raw=r.get('B')[0])
        elif name == 'Script':
            result.update(zip(('name', 'comment', 'conditions_comment', 'actions_comment'),
                              (r.string() for _ in range(4))))
            result.update(zip(('active_raw', 'deactivate_on_success_raw', 'easy_raw',
                               'medium_raw', 'hard_raw', 'subroutine_raw'), r.get('6B')))
            if chunk.version >= 2:
                result['evaluation_interval_raw'] = r.get('I')[0]
            if chunk.version >= 3:
                result.update(sequential_raw=r.get('B')[0], loop_raw=r.get('B')[0],
                              loop_count=r.get('i')[0], target_type_raw=r.get('B')[0],
                              target_name=r.string())
            if chunk.version >= 4:
                result['player_mask_text'] = r.string()
        elif name in ('Condition', 'ScriptAction', 'ScriptActionFalse'):
            result['opcode_raw'] = r.get('I')[0]
            kind = r.get('B')[0]
            name_id = int.from_bytes(r.take(3), 'little')
            result['internal_name'] = m.names[name_id]
            result['internal_name_kind'] = kind
            size = r.get('I')[0]
            if size > 100000:
                raise ValueError('Argument count exceeds tool limit')
            result['arguments'] = [argument(r) for _ in range(size)]
            if name == 'Condition' and chunk.version >= 5:
                result['enabled_raw'], result['condition_flag_4d_raw'] = r.get('2I')
            elif name != 'Condition' and chunk.version >= 3:
                result['enabled_raw'] = r.get('I')[0]
        if name in CHILDREN:
            result['children'] = []
            for child in chunks(r.take(len(r.data) - r.pos), m.names):
                child_name = m.names[child.name_id]
                allowed = child_name in CHILDREN[name]
                if name == 'ScriptGroup' and chunk.version < 3 and child_name == 'ScriptGroup':
                    allowed = False
                if not allowed:
                    result['children'].append(dict(chunk=child_name, version=child.version,
                        bytes=len(child.data), payload_decoded=False,
                        reason=f'Unexpected child of {name}', raw_hex=child.data.hex()))
                else:
                    result['children'].append(node(m, child, depth + 1))
        r.finish()
        result['payload_decoded'] = all(c['payload_decoded'] for c in result.get('children', []))
    except (ValueError, KeyError) as error:
        result.update(reason=str(error), raw_hex=chunk.data.hex())
    return result


def player_scripts(m):
    outer = m.chunk('PlayerScriptsList')
    if outer.version not in (1, 5, 6):
        raise ValueError(f'Unsupported PlayerScriptsList version {outer.version}')
    result = []
    for child in chunks(outer.data, m.names):
        if m.names[child.name_id] != 'ScriptList':
            raise ValueError('Expected ScriptList child')
        result.append(node(m, child))
    return result


def inventory(lists):
    versions, argument_types, signatures = Counter(), Counter(), Counter()
    incomplete = []
    coordinates = 0

    def visit(item, path):
        nonlocal coordinates
        path = path + [item.get('name', item['chunk'])]
        versions[f"{item['chunk']} v{item['version']}"] += 1
        if 'reason' in item:
            incomplete.append(dict(path=path, reason=item['reason']))
        if 'arguments' in item:
            types = tuple(a['type_id'] for a in item['arguments'])
            key = (item['chunk'], item['opcode_raw'], item['internal_name'], types)
            signatures[key] += 1
            argument_types.update(str(t) for t in types)
            coordinates += sum('position' in a for a in item['arguments'])
        for child in item.get('children', []):
            visit(child, path)

    for slot, item in enumerate(lists):
        visit(item, [f'list[{slot}]'])
    return dict(versions=dict(versions), argument_types=dict(argument_types),
                coordinate_arguments=coordinates, incomplete=incomplete,
                payloads_decoded=all(v['payload_decoded'] for v in lists),
                semantics_complete=False,
                signatures=[dict(chunk=k[0], opcode_raw=k[1], internal_name=k[2],
                                 argument_types=k[3], occurrences=n)
                            for k, n in sorted(signatures.items())])
