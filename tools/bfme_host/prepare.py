"""Copy the complete local game into an isolated, disposable runtime directory."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_SHA256 = 'f008b587570bad693981dc7218588c81d192a1e064b0f7f861539c51156a7640'


def main():
    manifest = ROOT / 'runtime/bfme-host/manifest.json'
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
    config['referenceTools'] = str(ROOT.parent / 'openbfme2/tools')
    manifest.write_text(json.dumps(config, indent=2), encoding='utf-8')
    print(f'Complete BFME2 runtime copied to {target}', flush=True)


if __name__ == '__main__':
    main()
