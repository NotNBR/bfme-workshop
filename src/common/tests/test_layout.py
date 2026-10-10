"""Project loading, camera continuity, root discovery and run isolation."""
import importlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from capture.kingdoms import resolve_shots
from common.paths import ROOT, find_root
from common.runs import create_run


class LayoutTests(unittest.TestCase):
    def test_map_projects_use_their_authored_source(self):
        module=importlib.import_module('examples.maps.eight_kingdoms.build')
        self.assertEqual(Path(module.__file__).resolve(),ROOT/'examples/maps/eight_kingdoms/build.py')
        self.assertTrue(module.REFERENCE.is_file())
        self.assertEqual((module.WIDTH,module.HEIGHT,module.BORDER,module.SEED),(900,960,150,82165))

    def test_continuous_camera_shots_meet_at_identical_states(self):
        shots=resolve_shots([[2500,9200],[7970,7920],[3700,4300],[9030,3040]])
        self.assertEqual(sum(s[-2] for s in shots),1920)
        for a,b in ((shots[0],shots[1]),(shots[1],shots[2]),(shots[6],shots[7])):
            self.assertEqual((a[0]+a[4],a[1]+a[5],a[6],a[7]),b[:4])

    def test_shot_count_cannot_overrun_native_array(self):
        with tempfile.TemporaryDirectory() as folder:
            project=Path(folder)
            (project/'project.toml').write_text('fps=30\ncapture_width=1600\ncapture_height=720\nshots="shots.json"\n')
            (project/'shots.json').write_text(json.dumps([{}]*13))
            with self.assertRaisesRegex(ValueError,'1..12'):
                resolve_shots([],project)

    def test_new_runs_cannot_overwrite_existing_runs_or_escape_artifacts(self):
        with tempfile.TemporaryDirectory() as folder, patch('common.runs.ROOT',Path(folder)), patch('common.runs.git_state',return_value={}):
            run=create_run('showcases','test','r001')
            (run/'exports/sentinel').write_text('keep')
            with self.assertRaises(FileExistsError):create_run('showcases','test','r001')
            with self.assertRaises(ValueError):create_run('showcases','test','../escape')
            self.assertEqual((run/'exports/sentinel').read_text(),'keep')
            self.assertEqual(json.loads((run/'manifest.json').read_text())['status'],'created')

    def test_root_resolution_is_independent_of_working_directory(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(find_root(ROOT/'examples/maps/eight_kingdoms/build.py'),ROOT)
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{'WORKSHOP_ROOT':folder}):
            with self.assertRaises(ValueError):find_root()


if __name__=='__main__':unittest.main()
