"""Eight-player document relationships and actual launcher slot writes."""
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from bfmexbar.mapkit.blank import create, starts
from bfmexbar.formats.map import Map
from bfmexbar.mapkit.analyze import records, nested
from bfmexbar.projects.maps.ithilien_frontier import build as ithilien
from bfmexbar.scenarios import eight_player


class EightKingdomsTests(unittest.TestCase):
    def test_visible_ocean_expansion_preserves_heights_and_relative_positions(self):
        from bfmexbar.projects.maps.eight_kingdoms.build import expose_ocean
        m=create(80,90,12);starts(m,[(100,200),(600,700)])
        before=m.heightmap()['elevations'].tobytes()
        shift=expose_ocean(m,3)
        m=Map(m.encode());h=m.heightmap();objects=m.objects()
        self.assertEqual(shift,90)
        self.assertEqual(h['border'],3)
        self.assertEqual(h['borders'],[(98,108)])
        self.assertEqual(h['elevations'].tobytes(),before)
        self.assertEqual([(o['x'],o['y']) for o in objects],[(190,290),(690,790)])
        self.assertEqual([o['z'] for o in objects],[0,0])

    def test_eight_sides_have_matching_teams_scripts_and_starts(self):
        m=create(80,80,3,player_count=8)
        starts(m,[(100+i*50,400) for i in range(8)])
        m=Map(m.encode())
        players=records(m,'SidesList')['players']
        expected={f'Player_{i}' for i in range(1,9)}
        self.assertEqual({p['playerName'] for p in players if p['playerName'].startswith('Player_')},expected)
        self.assertEqual(len(records(m,'Teams')),len(players))
        self.assertEqual(len(nested(m,'LibraryMapLists')),len(players))
        self.assertEqual(len(nested(m,'PlayerScriptsList')),len(players))
        self.assertEqual(len(nested(m,'MPPositionList')),8)
        self.assertEqual(len(m.objects()),8)

    def test_map_cache_counts_starts_and_preserves_other_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);folder=root/'runtime/bfme-host/mod/maps'
            folder.mkdir(parents=True)
            cache=folder/'mapcache.ini';cache.write_text('MapCache Existing\n  numPlayers = 2\nEND\n')
            m=create(80,80,3,player_count=8);starts(m,[(100+i*50,400) for i in range(8)])
            path=folder/'test.map';path.write_bytes(m.encode())
            with patch.object(ithilien,'ROOT',root):
                ithilien.cache_entry(path,m,'test','Test','Test')
                first=cache.read_text();ithilien.cache_entry(path,m,'test','Test','Test')
            self.assertEqual(first,cache.read_text())
            self.assertIn('MapCache Existing',first)
            self.assertIn('numPlayers = 8',first)
            self.assertIn('Player_8_Start =',first)
            # Duplicate starts must fail before replacing the cache.
            starts(m,[(100,100)])
            with patch.object(ithilien,'ROOT',root),self.assertRaises(ValueError):
                ithilien.cache_entry(path,m,'test','Test','Test')
            self.assertEqual(first,cache.read_text())

    def test_eight_player_setup_preserves_human_and_initialization_continuation(self):
        memory={};continuation=object()
        class Game:
            res={}
            def global_ptr(self,name):return 1000
            def u32(self,address):return memory.get(address,0)
            def write(self,address,data):
                if len(data)==4:memory[address]=struct.unpack('<I',data)[0]
        def original(*args,**kwargs):
            def init(game,tid,ctx):
                game.res={'setup':{}};return continuation
            return init
        smoke=SimpleNamespace(skirmish_setup=original,SLOTS_OFF=100,SLOT_TEMPLATE=20,
                              SLOT_STATE=12,AI_STATES={'easy':2})
        for i in range(8):
            memory[1100+i*4]=2000+i*100
            memory[2012+i*100]=6 if i==0 else 1
        with tempfile.TemporaryDirectory() as directory:
            mod=Path(directory);(mod/'data/ini').mkdir(parents=True)
            (mod/'data/ini/playertemplate.ini').write_text('\n'.join(
                'PlayerTemplate Faction'+f for f in ['Men','Elves','Dwarves','Isengard','Mordor','Wild']))
            eight_player.register(smoke,mod)
            game=Game();result=smoke.skirmish_setup(True,player=True)(game,0,None)
        self.assertIs(result,continuation)
        self.assertEqual(memory[2012],6)
        self.assertEqual([memory[2012+i*100] for i in range(1,8)],[2]*7)
        self.assertEqual(len(game.res['eight_player_slots']),8)
        self.assertEqual([memory[2020+i*100] for i in range(8)],[0,1,2,3,4,5,0,1])


if __name__=='__main__':unittest.main()
