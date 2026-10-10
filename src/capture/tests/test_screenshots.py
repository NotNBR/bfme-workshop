import tempfile
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from capture.screenshots import resolve_map, validate_shots
from capture import screenshots
from mapkit.tests.test_worldbuilder import fixture


class ScreenshotTests(unittest.TestCase):
    def test_shots_are_finite_unique_and_filename_safe(self):
        self.assertEqual(validate_shots([['cliff','10','20','300']]), [['cliff',10.,20.,300.]])
        for bad in ([], [['../bad',0,0,5]], [['x',0,0,0]], [['x',float('nan'),0,5]],
                    [['x',0,0,5],['x',0,0,6]], [['x',0,0]], [['x',None,0,5]], [['x',0,0,5]]*9):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_shots(bad)

    def test_flat_map_alias_resolves_to_existing_nested_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod=Path(tmp)
            file=mod/'maps'/'lab'/'lab.map'
            file.parent.mkdir(parents=True);file.write_bytes(b'test')
            source,native=resolve_map(mod,r'maps\lab.map')
            self.assertEqual(source,file.resolve())
            self.assertEqual(native,r'maps\lab\lab.map')
            self.assertEqual(resolve_map(mod,native)[0],source)
            for bad in (r'maps\missing.map',r'..\secret.map',r'C:\secret.map',r'maps\..\secret.map',r'maps\lab.ini'):
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    resolve_map(mod,bad)

    def test_changed_map_cannot_receive_success_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            host=root/'local/runtime/bfme-host'
            source=host/'mod/maps/lab/lab.map'
            source.parent.mkdir(parents=True);source.write_bytes(fixture())
            (host/'manifest.json').write_text(json.dumps({'mod':str(host/'mod')}))
            (host/'verification').mkdir()
            (host/'verification/skirmish_retail.json').write_text('{}')
            out=root/'capture'
            def native_run(arguments):
                (out/'native-validation.json').write_text(json.dumps(dict(outcome='pass',errors=[],shots=[])))
                source.write_bytes(source.read_bytes()+b'changed')
                return 0
            argv=['screenshots','--map',r'maps\lab.map','--shot','close','50','50','300','--out',str(out)]
            with patch.object(screenshots,'ROOT',root), patch('sys.argv',argv), \
                 patch('cli.launch',side_effect=native_run):
                self.assertEqual(screenshots.main(),1)
            report=json.loads((out/'capture.json').read_text())
            self.assertEqual(report['status'],'failed')
            self.assertIn('Source map changed during capture',report['errors'])
            self.assertTrue((out/'engine-report.json').exists())


if __name__=='__main__':
    unittest.main()
