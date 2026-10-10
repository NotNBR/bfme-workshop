"""Experiment controls and index invariants, independent of native rendering."""

import unittest

import numpy as np

from formats.map import Map
from formats.terrain import terrain_records
from mapkit.terrain_lab import BORDER, UV_STEP, build


class TerrainLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map, cls.cases = build()

    def test_reproducible_map_and_palette_references(self):
        data = self.map.encode()
        self.assertEqual(data, build()[0].encode())
        self.assertEqual(Map(data).encode(), data)
        self.assertEqual(len(self.cases), 16)
        b = self.map.blend()
        r = terrain_records(self.map)
        self.assertEqual({v['direction'] for v in r['blends']},
                         {'horizontal','vertical','right_diagonal','left_diagonal'})
        self.assertLess(int(b['arrays']['cliffs'].max()), len(r['cliffs'])+1)
        self.assertLess(int(b['arrays']['three_way'].max()), len(r['blends'])+1)

    def test_cliff_controls_have_identical_heights_and_materials(self):
        b = self.map.blend()['arrays']
        heights = self.map.heightmap()['elevations']
        panels = []
        for case in self.cases[-4:]:
            x,y,x1,y1 = [int(v/10)+BORDER for v in case['rect_world']]
            panels.append(heights[y:y1+1,x:x1+1])
            self.assertTrue(np.all(b['tiles'][y:y1,x:x1]//64 == 3))
            self.assertEqual(np.count_nonzero(b['cliffs'][y:y1,x:x1]),
                             0 if case['name']=='cliff-default' else 720)
        for panel in panels[1:]:
            np.testing.assert_array_equal(panel, panels[0])

    def test_three_way_triangles_match_and_uv_stays_inside_material(self):
        b = self.map.blend()['arrays']
        records = terrain_records(self.map)
        for y,x in zip(*np.nonzero(b['three_way'])):
            primary = records['blends'][int(b['blends'][y,x])-1]
            third = records['blends'][int(b['three_way'][y,x])-1]
            self.assertNotEqual(primary['tile']//64, third['tile']//64)
            self.assertEqual(primary['force_flip'], third['direction']=='right_diagonal')
        for cliff in records['cliffs']:
            for u,v in cliff['uv']:
                self.assertTrue(0 <= u <= 8*UV_STEP)
                self.assertTrue(-8*UV_STEP <= v <= 0)


if __name__ == '__main__':
    unittest.main()
