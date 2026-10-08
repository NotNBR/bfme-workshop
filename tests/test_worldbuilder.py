import contextlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from tools.worldbuilder.format import Map, Chunk, sha, differences, string
from tools.worldbuilder.author import apply_recipe
from tools.worldbuilder import cli


def fixture():
    names = ['HeightMapData', 'BlendTileData', 'WorldInfo', 'ObjectsList', 'Object', 'uniqueID', 'MysteryChunk']
    m = object.__new__(Map)
    m.names = dict(enumerate(names, 1))
    width, height, border = 30, 34, 2  # Not divisible by 8: exercise per-row bit padding.
    area = width * height
    terrain = struct.pack('<7I', width, height, border, 1, width - 2 * border, height - 2 * border, area)
    terrain += np.full((height, width), 2560, dtype='<u2').tobytes()
    blend = struct.pack('<I', area) + bytes(area * 14)
    bits = bytes(((width + 7) // 8) * height)
    blend += bits * 5 + bytes(area) + bits
    blend += struct.pack('<4I', 16, 1, 1, 1)
    blend += struct.pack('<4I', 0, 16, 4, 0) + string('GrassTest') + bytes(8)
    obj = struct.pack('<4fI', 25, 25, 0, 0, 0) + string('TreeEvergreen03')
    obj += m.encode_properties([('uniqueID', 3, 'TreeEvergreen03 0')])
    m.chunks = [Chunk(1, 5, terrain), Chunk(2, 18, blend), Chunk(3, 1, bytes(2)),
                Chunk(4, 3, Chunk(5, 3, obj).encode()), Chunk(7, 19, b'unknown data must survive\x00\xff')]
    return m.encode()


def recipe(*operations):
    return dict(schema=1, id='test_pass', seed=123, operations=list(operations))


class WorldBuilderTests(unittest.TestCase):
    def test_lossless_and_row_padded_flags(self):
        data = fixture()
        m = Map(data)
        self.assertEqual(m.encode(), data)
        self.assertTrue(m.report()['raw_roundtrip_exact'])
        self.assertEqual(m.blend()['textures'][0]['name'], 'GrassTest')
        self.assertEqual(m.blend()['arrays']['visible'].shape, (34, 30))

    def test_corrupt_count_and_truncation_rejected(self):
        m = Map(fixture())
        m.chunk('BlendTileData').data = struct.pack('<I', 99) + m.chunk('BlendTileData').data[4:]
        with self.assertRaises(ValueError): m.report()
        with self.assertRaises(ValueError): Map(fixture()[:-1])

    def test_terrain_and_paint_preserve_unrelated_bytes(self):
        data = fixture()
        out, diff = apply_recipe(data, recipe(
            dict(op='raise', x=120, y=120, radius=65, amount=12),
            dict(op='paint', x=120, y=120, radius=30, texture='GrassTest')))
        m, before = Map(out), Map(data)
        self.assertEqual(set(diff['changed_chunks']), {'HeightMapData', 'BlendTileData'})
        self.assertEqual(m.chunk('MysteryChunk').data, before.chunk('MysteryChunk').data)
        self.assertEqual(m.chunk('ObjectsList').data, before.chunk('ObjectsList').data)
        self.assertEqual(m.heightmap()['elevations'][14, 14], round(112 / 0.0390625))
        self.assertTrue(np.array_equal(m.heightmap()['elevations'][:2], before.heightmap()['elevations'][:2]))
        self.assertEqual(m.blend()['arrays']['tiles'][14, 14], 54)

    def test_seeded_scatter_names_spacing_exclusions_and_replay(self):
        data = fixture()
        rec = recipe(dict(op='scatter', template='TreeEvergreen03', count=12, rect=[10, 10, 250, 290], spacing=20))
        rec['exclude_rects'] = [[70, 70, 170, 170]]
        out, _ = apply_recipe(data, rec)
        self.assertEqual(out, apply_recipe(data, rec)[0])
        objs = Map(out).objects()
        self.assertEqual(len(objs), 13)
        identifiers = [v for o in objs for k, _, v in o['properties'] if k == 'uniqueID']
        self.assertEqual(len(set(identifiers)), 13)
        for i, obj in enumerate(objs[1:], 1):
            self.assertFalse(70 <= obj['x'] <= 170 and 70 <= obj['y'] <= 170)
            for earlier in objs[:i]:
                self.assertGreaterEqual((obj['x']-earlier['x'])**2 + (obj['y']-earlier['y'])**2, 399.99)
        with self.assertRaises(ValueError): apply_recipe(out, rec)

    def test_overcrowded_recipe_fails_without_mutating_source(self):
        data = fixture()
        expected = sha(data)
        with self.assertRaises(ValueError):
            apply_recipe(data, recipe(dict(op='scatter', template='TreeEvergreen03', count=20, rect=[10,10,20,20], spacing=100)))
        self.assertEqual(sha(data), expected)

    def test_invalid_brush_and_unsupported_action(self):
        for operation in [dict(op='resize'), dict(op='raise', x=20, y=20, radius=0, amount=1),
                          dict(op='raise', x=20, y=20, radius=20, amount=float('nan'))]:
            with self.assertRaises(ValueError): apply_recipe(fixture(), recipe(operation))

    def test_diff_includes_added_chunk(self):
        a, b = Map(fixture()), Map(fixture())
        b.chunks.append(Chunk(b.intern('AnotherChunk'), 1, b'new'))
        self.assertIn('AnotherChunk', differences(a, b)['changed_chunks'])

    def test_workspace_transactions_reject_stale_hash_and_preserve_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / 'source'; src.mkdir()
            source = src / 'original.map'; source.write_bytes(fixture())
            (src / 'map.ini').write_text('; original sidecar')
            rec = root / 'recipe.json'; rec.write_text(json.dumps(recipe(dict(op='raise', x=120,y=120,radius=50,amount=10))))
            with patch.object(cli, 'WORKSPACES', root / 'workspaces'), contextlib.redirect_stdout(io.StringIO()):
                cli.main(['checkout', str(source), 'demo'])
                target = cli.working_file('demo')
                with self.assertRaises(ValueError): cli.main(['apply', 'demo', str(rec), '--expect-sha', 'stale'])
                self.assertEqual(target.read_bytes(), fixture())
                cli.main(['apply', 'demo', str(rec), '--expect-sha', sha(target.read_bytes())])
                self.assertNotEqual(target.read_bytes(), fixture())
                self.assertEqual(source.read_bytes(), fixture())
                self.assertEqual(len(list((cli.workspace('demo') / 'checkpoints').iterdir())), 3)
                self.assertTrue((cli.workspace('demo') / 'preview.png').exists())
                with self.assertRaises(ValueError): cli.main(['apply', 'demo', str(rec), '--expect-sha', sha(target.read_bytes())])
                with self.assertRaises(ValueError): cli.workspace('../escape')


if __name__ == '__main__':
    unittest.main()
