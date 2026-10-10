import json
from pathlib import Path
import struct
import tempfile
import unittest

from mapkit.script_check import named_objects, validate


class ScriptObservationTests(unittest.TestCase):
    def test_movement_uses_the_entire_track_and_outcome_is_exclusive(self):
        import contextlib
        import io
        proof=dict(expected=['LAB_Unit'],forbidden=[],minimum_frame=100,timer_checks=[],
            one_of=[['LAB_Open','LAB_Closed']],
            movement_cases=[dict(unit='LAB_Unit',reachable_marker='LAB_Open',near_bank_x=1200,far_bank_x=1300)])
        def sample(frame,x):
            return dict(frame=frame,objects={'LAB_Unit':[dict(position=[x,100,100])],'LAB_Open':[{}]})
        evidence=dict(first_seen={},forbidden_seen={},samples=[sample(1,1050),sample(100,1400),sample(200,300)])
        with tempfile.TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()):
            root=Path(temporary);out=root/'out';out.mkdir()
            proof_path=root/'proof.json';proof_path.write_text(json.dumps(proof))
            report=dict(outcome='pass',profile_touched=False,run={'script_lab':evidence})
            path=out/'skirmish_retail.json';path.write_text(json.dumps(report))
            self.assertEqual(validate(out,proof_path),0)
            # Crossing X alone does not prove travel on a bridge deck.
            proof['movement_cases'][0]['crossing_volume']=dict(y_min=50,y_max=150,z_min=80)
            proof_path.write_text(json.dumps(proof))
            evidence['samples'].insert(1,sample(50,1250))
            path.write_text(json.dumps(report))
            self.assertEqual(validate(out,proof_path),0)
            evidence['samples'][1]['objects']['LAB_Unit'][0]['position'][2]=20
            path.write_text(json.dumps(report))
            self.assertEqual(validate(out,proof_path),1)
            evidence['samples'].pop(1)
            del proof['movement_cases'][0]['crossing_volume']
            proof_path.write_text(json.dumps(proof))
            evidence['samples'][1]['objects']['LAB_Unit'][0]['position'][0]=1100
            path.write_text(json.dumps(report))
            self.assertEqual(validate(out,proof_path),1)
            evidence['samples'][1]['objects']['LAB_Unit'][0]['position'][0]=1400
            evidence['samples'][-1]['objects']['LAB_Closed']=[{}]
            path.write_text(json.dumps(report))
            self.assertEqual(validate(out,proof_path),1)

    def test_native_name_control_and_cycle_guard(self):
        memory = {}
        class Game:
            base = 0
            def read(self, address, size):
                return bytes(memory.get(address + i, 0) for i in range(size))
            def u32(self, address):
                return struct.unpack('<I', self.read(address, 4))[0]
        def put(address, data):
            memory.update({address + i: b for i, b in enumerate(data)})
        put(0x9FE78C, struct.pack('<I', 0x1000))
        put(0x10AC, struct.pack('<I', 0x2000))
        put(0x2088, struct.pack('<I', 0x3000))
        put(0x2038, struct.pack('<3f', 10, 20, 100))
        name = b'LAB_Control'
        put(0x3000, struct.pack('<4H', 1, 32, len(name), 0) + name)
        self.assertEqual(named_objects(Game())['LAB_Control'][0]['position'], (10, 20, 100))
        put(0x208C, struct.pack('<I', 0x2000))
        with self.assertRaisesRegex(ValueError, 'cycle'):
            named_objects(Game())

    def test_native_validation_requires_positive_and_negative_evidence(self):
        proof = dict(expected=['LAB_Init', 'LAB_Timer'], forbidden=['LAB_Bad'], minimum_frame=100,
                     timer_reference='LAB_Init', timer_checks=[dict(name='LAB_Timer', basis='frames', minimum=55, maximum=70)])
        evidence = dict(first_seen={'LAB_Init':1, 'LAB_Timer':61}, forbidden_seen={},
                        samples=[dict(frame=200, objects={'LAB_Init':[{}], 'LAB_Timer':[{}]})])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); output = root / 'engine'; output.mkdir()
            path = root / 'proof.json'; path.write_text(json.dumps(proof))
            report = dict(outcome='pass', profile_touched=False, run={'script_lab':evidence})
            raw = output / 'skirmish_retail.json'; raw.write_text(json.dumps(report))
            self.assertEqual(validate(output, path), 0)
            evidence['forbidden_seen']['LAB_Bad'] = 20
            evidence['samples'][0]['objects']['LAB_Timer'].append({})
            raw.write_text(json.dumps(report))
            self.assertEqual(validate(output, path), 1)
            result = json.loads((root / 'native-validation.json').read_text())
            self.assertEqual(len(result['errors']), 2)


if __name__ == '__main__':
    unittest.main()
