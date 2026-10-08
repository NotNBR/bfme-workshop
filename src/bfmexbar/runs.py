"""Create separate build/capture runs while preserving existing artifacts."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from bfmexbar.paths import ROOT


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def git_state():
    def git(*args):
        result = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, check=True)
        return result.stdout
    return {'commit': git('rev-parse', 'HEAD').decode().strip(),
            'dirty': bool(git('status', '--porcelain')),
            'diff_sha256': hashlib.sha256(git('diff', 'HEAD')).hexdigest()}


def create_run(kind, project, run_id=None):
    if kind not in ('maps', 'showcases', 'scenarios'):
        raise ValueError('Unknown run kind')
    run_id = run_id or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    if not all(re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]*', part) for part in (project,run_id)):
        raise ValueError('Project and run IDs must be simple directory names')
    root = ROOT / 'artifacts' / kind / project / run_id
    root.mkdir(parents=True, exist_ok=False)
    folders = ('capture','intermediates','exports','validation') if kind == 'showcases' else ('map','previews','validation') if kind == 'maps' else ('validation',)
    for name in folders:
        (root / name).mkdir()
    sources = {}
    for directory in ('src/bfmexbar', 'src/native', 'projects', 'scripts'):
        for path in (ROOT / directory).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.name != 'config.local.toml':
                sources[path.relative_to(ROOT).as_posix()] = digest(path)
    manifest = {'schema':1, 'kind':kind, 'project':project, 'run_id':run_id,
                'created_utc':datetime.now(timezone.utc).isoformat(), 'status':'created',
                'git':git_state(), 'source_sha256':sources}
    (root / 'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return root


def update_run(root, **fields):
    path = Path(root) / 'manifest.json'
    data = json.loads(path.read_text())
    data.update(fields)
    path.write_text(json.dumps(data,indent=2)+'\n')
