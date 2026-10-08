"""Inventory stored script signatures in .map/.bse documents in a local BIG."""

import argparse
from collections import Counter
import json
from pathlib import Path

from bfmexbar.formats.big import BigArchive
from bfmexbar.formats.map import Map, sha
from bfmexbar.formats.scripts import player_scripts, inventory


def audit(path):
    archive = BigArchive(path)
    files, failures = [], []
    versions, types, signatures = Counter(), Counter(), Counter()
    coordinates = 0
    for name in sorted(archive.entries):
        if not name.endswith(('.map', '.bse')):
            continue
        try:
            data = archive.read_bytes(name)
            m = Map(data)
            report = inventory(player_scripts(m))
            versions.update(report['versions'])
            types.update(report['argument_types'])
            coordinates += report['coordinate_arguments']
            for s in report['signatures']:
                signatures[(s['chunk'], s['opcode_raw'], s['internal_name'],
                            tuple(s['argument_types']))] += s['occurrences']
            files.append(dict(map=name, file_sha256=sha(data), **report))
        except (ValueError, KeyError) as error:
            failures.append(dict(map=name, reason=str(error)))
    return dict(schema=1, semantics_complete=False, maps=len(files),
                payloads_decoded_maps=sum(f['payloads_decoded'] for f in files),
                versions=dict(versions), argument_types=dict(types),
                coordinate_arguments=coordinates, failures=failures,
                signatures=[dict(chunk=k[0], opcode_raw=k[1], internal_name=k[2],
                                 argument_types=k[3], occurrences=n)
                            for k, n in sorted(signatures.items())], files=files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.archive.resolve() == args.out.resolve():
        parser.error('Output must not overwrite the archive')
    report = audit(args.archive)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('files', 'signatures')}))


if __name__ == '__main__':
    main()
