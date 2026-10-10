"""Independent invariants for the from-scratch native document writer."""
import struct
import unittest
import numpy as np
from mapkit.blank import create, starts, set_materials, set_heights
from formats.map import Map, Reader, chunks
from mapkit.analyze import analyze


class BlankDocumentTests(unittest.TestCase):
    def test_new_plane_is_empty_and_all_supported_sections_decode(self):
        m=create(71,83,3)
        data=m.encode(); report=analyze(data)
        self.assertEqual(report['height_range'],[100,100])
        self.assertEqual(report['objects'],0)
        self.assertEqual(report['dimensions']['samples'],[77,89])
        self.assertEqual(report['unresolved_sections'],{})
        self.assertEqual(Map(data).encode(),data)
        self.assertEqual(len(m.chunk('GlobalLighting').data),1360)
        self.assertEqual(m.chunk('PostEffectsChunk').data,b'\0')

    def test_starts_preserve_plane_and_use_distinct_native_ids(self):
        m=create(71,83,3); original=m.chunk('HeightMapData').data
        starts(m,[(200,250),(500,550)])
        objects=Map(m.encode()).objects()
        self.assertEqual(len(objects),2)
        self.assertEqual(m.chunk('HeightMapData').data,original)
        self.assertEqual([dict((k,v) for k,_,v in o['properties'])['waypointID'] for o in objects],[1,2])

    def test_non_byte_aligned_bit_planes_and_blend_ranges(self):
        m=create(71,83,3); labels=np.zeros((89,77),dtype='u2');labels[:,38:]=1
        blocked=np.zeros_like(labels);blocked[8,76]=1;blocked[88,0]=1
        set_materials(m,['A','B'],labels,blocked)
        b=Map(m.encode()).blend()
        np.testing.assert_array_equal(b['arrays']['impassable'],blocked)
        self.assertTrue((b['arrays']['visible']==1).all())
        self.assertEqual(int(b['arrays']['blends'][30,37])>0,True)
        # First tile of each 2x2 cell row increments by four, not two.
        self.assertEqual(list(b['arrays']['tiles'][0,:4]),[0,1,4,5])
        self.assertLess(int(b['arrays']['tiles'].max()),128)
        self.assertTrue(analyze(m.encode())['blend_details']['tail_fully_consumed'])

    def test_invalid_elevations_are_rejected_before_writing(self):
        m=create(64,64,3)
        for bad in [float('nan'),-1,2600]:
            with self.assertRaises(ValueError):set_heights(m,np.full((70,70),bad))


    def test_eight_player_document_has_matching_sides_scripts_and_starts(self):
        m=create(100,100,3,player_count=8)
        starts(m,[(100+i*90,400) for i in range(8)])
        report=analyze(m.encode())
        self.assertEqual(len(report['waypoints']),8)
        sides=Reader(m.chunk('SidesList').data)
        self.assertEqual(sides.get('BI'),(1,18))
        for chunk_name in ['PlayerScriptsList','LibraryMapLists']:
            self.assertEqual(len(chunks(m.chunk(chunk_name).data,m.names)),18)
        self.assertEqual(len(chunks(m.chunk('MPPositionList').data,m.names)),8)
        with self.assertRaises(ValueError):create(player_count=9)

if __name__=='__main__':unittest.main()
