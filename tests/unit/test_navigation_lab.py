import unittest
from collections import deque

from bfmexbar.formats.scripts import inventory, player_scripts
from bfmexbar.mapkit.navigation_lab import build


class NavigationLabTests(unittest.TestCase):
    def test_bridge_controls_differ_only_in_presence_and_height(self):
        from bfmexbar.mapkit.script_catalog import load_catalog
        m,proof=build(load_catalog(),surface='bridges',movement=True,human_owned=True)
        bridges=[o for o in m.objects() if o['template']=='GondorIthilienBridge2']
        self.assertEqual([o['z'] for o in bridges],[79,179])
        heights=m.heightmap()['elevations']*.0390625
        self.assertEqual([heights[8+row*64+32,8+125] for row in range(4)],[100,20,20,20])
        self.assertEqual([heights[8+row*64+32,8+90] for row in range(4)],[100]*4)
        self.assertEqual(sum('crossing_volume' in c for c in proof['movement_cases']),4)
        self.assertIn('LAB_Reachable_dry_GondorFighter',proof['expected'])
        self.assertIn('LAB_Blocked_water_gap_GondorFighter',proof['expected'])

    def test_surface_variants_store_measured_heights(self):
        from bfmexbar.mapkit.script_catalog import load_catalog
        from bfmexbar.mapkit.analyze import records
        catalog=load_catalog()
        m,proof=build(catalog,surface='water',water_depths=(5,6,20))
        self.assertEqual([a['water_height'] for a in records(m,'StandingWaterAreas')],[105,106,120])
        self.assertEqual(proof['water_depths'],(5,6,20))
        m,proof=build(catalog,surface='slopes',slope_rises=(50,100,200))
        heights=m.heightmap()['elevations']*.0390625
        self.assertEqual([heights[8+row*64+20,8+125] for row in (1,2,3)],[350,600,1100])
        self.assertEqual([heights[8+row*64+20,8+120] for row in (1,2,3)],[100,100,100])
        with self.assertRaises(ValueError):build(catalog,surface='water',water_depths=(1,1,2))
        with self.assertRaises(ValueError):build(catalog,surface='slopes',slope_rises=(1,2,401))

    def test_barriers_isolate_cases_and_script_references_resolve(self):
        catalog=dict(schema=1,game='BFME2 1.06',action=dict(templates=[
            dict(opcode=40,name='CREATE_NAMED_ON_TEAM_AT_WAYPOINT',argument_types=[14,15,3,7]),
            dict(opcode=9,name='DISABLE_SCRIPT',argument_types=[2]),
            dict(opcode=38,name='MOVE_NAMED_UNIT_TO',argument_types=[14,7])]),condition=dict(templates=[
            dict(opcode=136,name='UNIT_CAN_PATH_TO_WAYPOINT',argument_types=[14,7]),
            dict(opcode=30,name='NAMED_OWNED_BY_PLAYER',argument_types=[14,11])]))
        m,proof=build(catalog,movement=True,human_owned=True)
        self.assertTrue(inventory(player_scripts(m))['payloads_decoded'])
        waypoints={v for o in m.objects() for k,_,v in o['properties'] if k=='waypointName'}
        self.assertTrue(all(c['target'] in waypoints for c in proof['navigation_cases']))
        self.assertEqual(len(proof['one_of']),16)
        # Check geometry independently of the generator's slicing: a flood fill
        # must not escape the positive-control corridor or bypass the barrier.
        blocked=m.blend()['arrays']['impassable']
        def reachable(start,end):
            todo=deque([start]);seen={start}
            while todo:
                y,x=todo.popleft()
                if (y,x)==end:return True
                for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
                    p=(y+dy,x+dx)
                    if 0<=p[0]<blocked.shape[0] and 0<=p[1]<blocked.shape[1] and not blocked[p] and p not in seen:
                        todo.append(p);seen.add(p)
            return False
        self.assertTrue(reachable((24,113),(24,163)))
        self.assertFalse(reachable((88,113),(88,163)))
        self.assertFalse(reachable((24,113),(88,113)))


if __name__=='__main__':unittest.main()
