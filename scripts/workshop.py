"""Run the checkout without requiring an editable installation."""
from pathlib import Path
import sys

sys.pycache_prefix = str(Path(__file__).resolve().parents[1]/'local/cache/python')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cli import main

if __name__ == '__main__':
    raise SystemExit(main())
