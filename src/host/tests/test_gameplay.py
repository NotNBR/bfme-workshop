"""Economy regression ported from the starting-funds chat."""
import pathlib
import struct
import tempfile
import types
import unittest
from common.paths import ROOT
from host.build import command_limits,gameplay_settings
from host import gameplay

class GameplayTests(unittest.TestCase):
    def test_caps_raise_starting_capacity_and_ceiling(self):
        text='\n'.join(f'{f}CommandPointsMP{n} = 100 1000 ; comment' for f in ['Good','Evil'] for n in range(2,9))
        limits=command_limits(text,4)
        self.assertEqual(len(limits),14)
        self.assertTrue(all(value==(1000,4000) for value in limits.values()))

    def test_starting_capacity_cannot_exceed_ceiling(self):
        text='\n'.join(f'{f}CommandPointsMP{n} = 100 500' for f in ['Good','Evil'] for n in range(2,9))
        self.assertTrue(all(value==(500,500) for value in command_limits(text,1).values()))
        self.assertTrue(all(value==(200,2000) for value in command_limits(text,4,200).values()))

    def test_settings_refresh_preserves_authored_maps_and_native_data(self):
        scratch=ROOT/'local/cache/gameplay-tests'
        scratch.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            mod=pathlib.Path(directory)
            source=mod/'data/ini/gamedata.ini';source.parent.mkdir(parents=True)
            text='\n'.join(f'{f}CommandPointsMP{n} = 100 1000 ; native' for f in ['Good','Evil'] for n in range(2,9))
            source.write_text(text)
            authored=mod/'maps/custom.map';authored.parent.mkdir();authored.write_bytes(b'authored map')
            gameplay_settings(mod,24,4,1000,10000,write=False)
            overlay=mod/'data/ini/object/workshop_gamedata.ini'
            self.assertFalse(overlay.exists())
            limits=gameplay_settings(mod,24,4,1000,10000)
            self.assertIn('DefaultStartingCash = 10000',overlay.read_text())
            self.assertEqual(limits['GoodCommandPointsMP8'],(1000,4000))
            self.assertEqual(source.read_text(),text)
            self.assertEqual(authored.read_bytes(),b'authored map')
            with self.assertRaises(ValueError):gameplay_settings(mod,24,4,-1,10000)

    def test_economy_setup_keeps_faction_handler_and_sets_native_rules(self):
        class Memory:
            res={}
            memory={}
            def global_ptr(self,name):return 0x1000
            def write(self,address,data):self.memory[address]=data;return True
            def read(self,address,count):return self.memory[address]
        game=Memory()
        def original(*args,**kwargs):
            def setup(g,t,c):
                g.res['factions']='Mordor vs Elves'
                return {'call':123,'args':[456]}
            return setup
        smoke=types.SimpleNamespace(skirmish_setup=original,Game=object,RVA={})
        gameplay.register(smoke,10000)
        result=smoke.skirmish_setup(True,player=True)(game,0,None)
        self.assertEqual(result,{'call':123,'args':[456]})
        self.assertEqual(game.res['factions'],'Mordor vs Elves')
        self.assertEqual(game.read(0x1070,4),struct.pack('<I',10000))
        self.assertEqual(game.read(0x106C,4),struct.pack('<I',100))
