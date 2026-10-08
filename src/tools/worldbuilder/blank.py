"""Compatibility entry point; implementation: bfmexbar.mapkit.blank."""
from pathlib import Path
import importlib
import runpy
import sys

_root = next(p for p in Path(__file__).resolve().parents if (p / 'pyproject.toml').is_file())
if str(_root / 'src') not in sys.path:
    sys.path.insert(0, str(_root / 'src'))
if __name__ == '__main__':
    runpy.run_module('bfmexbar.mapkit.blank', run_name='__main__', alter_sys=True)
else:
    sys.modules[__name__] = importlib.import_module('bfmexbar.mapkit.blank')
