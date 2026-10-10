"""Run component tests, source syntax checks and local documentation-link checks."""
import ast
import contextlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
sys.pycache_prefix = str(ROOT/'local/cache/python')
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'src'))
os.chdir(ROOT)
OUTPUT=ROOT/'local/cache/checks'
OUTPUT.mkdir(parents=True,exist_ok=True)
scratch=OUTPUT/'temp'
scratch.mkdir(exist_ok=True)
tempfile.tempdir=str(scratch)

errors=[]
source_count=0
documents=0
links=0
for base in ('src','mods','examples','scripts'):
    for path in (ROOT/base).rglob('*.py'):
        if '__pycache__' in path.parts or '.egg-info' in str(path): continue
        source_count+=1
        try: ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
        except SyntaxError as error: errors.append(str(error))
for path in [ROOT/'README.md',*(ROOT/'docs').rglob('*.md'),*(ROOT/'mods').rglob('*.md'),*(ROOT/'examples').rglob('*.md'),*(ROOT/'src').rglob('*.md')]:
    documents+=1
    for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target) or target.startswith(('#','/','<')): continue
        links+=1
        if not (path.parent/unquote(target.split('#',1)[0])).exists():
            errors.append(f'Broken link: {path.relative_to(ROOT)} -> {target}')

suite=unittest.TestSuite()
suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'src'),top_level_dir=str(ROOT/'src')))
suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'mods/recoil/tools/tests'),top_level_dir=str(ROOT)))
out=io.StringIO()
with contextlib.redirect_stdout(out),contextlib.redirect_stderr(out):
    result=unittest.TextTestRunner(stream=out,verbosity=1).run(suite)
(OUTPUT/'python-tests.log').write_text(out.getvalue(),encoding='utf-8')
if not result.wasSuccessful():
    print(out.getvalue())
    errors.append('Python tests failed')
report={'python_tests':result.testsRun,'python_pass':result.wasSuccessful(),'source_files':source_count,'documents':documents,'local_links':links,'errors':errors}
(OUTPUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'Python: {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors.')
print(f'Syntax: {source_count} source files. Documentation: {documents} files, {links} local links.')
for error in errors: print(error)
raise SystemExit(bool(errors))
