"""Compatibility entry point for the archived Recoil experiment."""
from pathlib import Path
import importlib, runpy, sys
_root=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path.insert(0,str(_root));sys.path.insert(0,str(_root/'src'))
if __name__=='__main__':runpy.run_module('legacy.recoil.tools.launch',run_name='__main__', alter_sys=True)
else:sys.modules[__name__]=importlib.import_module('legacy.recoil.tools.launch')
