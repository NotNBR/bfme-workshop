"""Check the Recoil map exporter independently of retail game assets."""
from pathlib import Path
import struct
import tempfile
import unittest
from mods.recoil.tools.build import make_map


class MapExportTests(unittest.TestCase):
    def test_native_map_boundaries(self):
        with tempfile.TemporaryDirectory() as path:
            make_map(Path(path))
            data=(Path(path)/'maps'/'pelennor.smf').read_bytes()
            header=struct.unpack_from('<16s7i2f7i',data)
            self.assertEqual(header[0],b'spring map file\0')
            height,typeptr,tiles,mini,metal,feature=header[10:16]
            self.assertEqual(typeptr-height,513*513*2)
            self.assertEqual(metal-mini,699048)
            self.assertEqual(len(data)-feature,8)
