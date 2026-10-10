"""Import optional local balance data for the browser and Recoil examples."""
from pathlib import Path
import runpy
import sys

sys.pycache_prefix = str(Path(__file__).resolve().parents[1]/'local/cache/python')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
runpy.run_module('formats.big', run_name='__main__')
