"""Repository and machine-local paths shared by every workflow."""
import os
from pathlib import Path
import tomllib


def find_root(start=None):
    override = os.environ.get('WORKSHOP_ROOT')
    if override:
        root = Path(override).expanduser().resolve()
        if not (root / 'pyproject.toml').is_file() or not (root / 'src/host').is_dir():
            raise ValueError(f'WORKSHOP_ROOT is not a bmfe-workshop checkout: {root}')
        return root
    start = Path(start or __file__).resolve()
    for candidate in (start, *start.parents):
        if (candidate / 'pyproject.toml').is_file() and (candidate / 'src/host').is_dir():
            return candidate
    raise RuntimeError('Set WORKSHOP_ROOT to the bmfe-workshop checkout containing maps and mods')


ROOT = find_root()


def local_config():
    path = ROOT / 'local/config.toml'
    return tomllib.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def local_path(name, default):
    value = local_config().get('paths', {}).get(name)
    path = Path(value).expanduser() if value else Path(default)
    return (ROOT / path).resolve() if not path.is_absolute() else path.resolve()
