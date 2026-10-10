"""Copy the complete local game into an isolated, disposable runtime directory."""

from common.paths import ROOT, local_path
import hashlib
import json
from pathlib import Path
import shutil

SUPPORTED_SHA256 = json.loads((ROOT/'mods/strategic/config/bfme2-1.06.json').read_text())['sha256']


def main():
    manifest = ROOT / 'local/runtime/bfme-host/manifest.json'
    config = json.loads(manifest.read_text())
    source = Path(config['game'])
    if hashlib.sha256((source / 'game.dat').read_bytes()).hexdigest() != SUPPORTED_SHA256:
        raise SystemExit('The openbfme2 launch hooks require the verified BFME2 1.06 game.dat.')
    target = manifest.parent / 'game'
    target.mkdir(exist_ok=True)
    for file in source.rglob('*'):
        if not file.is_file():
            continue
        relative = file.relative_to(source)
        if file.suffix.lower() in ('.dmp', '.log', '.dbgcmd') or file.name.startswith('DUMP_'):
            continue
        if len(relative.parts) > 1 and relative.parts[0].lower() not in ('apt', 'data', 'lang', 'launcher', 'mss'):
            continue
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists() or destination.stat().st_size != file.stat().st_size or destination.stat().st_mtime_ns != file.stat().st_mtime_ns:
            shutil.copy2(file, destination)
    config['sandbox'] = str(target)
    config['referenceTools'] = str(local_path('reference_tools', ROOT.parent / 'openbfme2/tools'))
    manifest.write_text(json.dumps(config, indent=2), encoding='utf-8')
    print(f'Complete BFME2 runtime copied to {target}', flush=True)


if __name__ == '__main__':
    main()
