"""Prepare an isolated worktree mod/profile using an existing local BFME runtime."""

from bfmexbar.paths import ROOT, local_path
import argparse
import json
from pathlib import Path
import shutil

def prepare(source):
    source = source.resolve()
    target = ROOT / 'runtime/bfme-host'
    if source == target.resolve():
        raise ValueError('Source runtime must differ from this worktree runtime')
    manifest = target / 'manifest.json'
    if manifest.exists():
        print(f'Existing isolated runtime: {target}')
        return
    config = json.loads((source / 'manifest.json').read_text())
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source / 'mod/data', target / 'mod/data', dirs_exist_ok=True)
    (target / 'mod/maps').mkdir(exist_ok=True)
    (target / 'mod/maps/mapcache.ini').write_text('', encoding='ascii')
    shutil.copytree(source / 'extension', target / 'extension', dirs_exist_ok=True)
    # The executable/assets are read from the existing sandbox; the mod, options,
    # save profile, generated map and verification reports belong to this worktree.
    config['mod'] = str(target / 'mod')
    manifest.write_text(json.dumps(config, indent=2), encoding='utf-8')
    print(f'Prepared {target}')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path,
                   default=local_path('source_runtime', ROOT.parent / 'bfmeXbar/runtime/bfme-host'))
    prepare(p.parse_args().source)
