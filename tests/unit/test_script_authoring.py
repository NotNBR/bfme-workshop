import unittest

from bfmexbar.formats.map import Map
from bfmexbar.formats.scripts import inventory, player_scripts
from bfmexbar.mapkit.blank import create
from bfmexbar.mapkit.script_catalog import extract, compare, reconcile
from bfmexbar.mapkit.script_writer import Writer, arg


class ScriptAuthoringTests(unittest.TestCase):
    def test_bundled_catalog_supports_clean_checkout_authoring(self):
        from bfmexbar.mapkit.script_catalog import load_catalog
        catalog=load_catalog()
        self.assertEqual(catalog['action']['named'],595)
        self.assertEqual(catalog['condition']['named'],195)
        self.assertFalse(catalog['behavior_verified'])
        self.assertTrue(all(r['argument_types'] is not None and None not in r['argument_types']
                            for kind in ('action','condition') for r in catalog[kind]['templates']))
        w=Writer(create(64,64,4))
        self.assertEqual(w.operation('action','SET_COUNTER',[arg(4,text='Score'),arg(0,integer=8)]).version,3)

    def test_source_order_mixed_tables_holes_and_missing_defaults(self):
        source = '''
        curTemplate = &m_actionTemplates[1];
        curTemplate->m_internalName = "OLD";
        curTemplate->m_numParameters = 1;
        curTemplate->m_parameters[0] = 4;
        curTemplate = &m_conditionTemplates[2];
        curTemplate->m_internalName = "OTHER";
        curTemplate->m_numParameters = 0;
        curTemplate = &m_actionTemplates[1];
        curTemplate->m_internalName = "FINAL";
        curTemplate = &m_actionTemplates[3];
        curTemplate->m_internalName = "MISSING";
        curTemplate->m_numParameters = 1;
        // curTemplate->m_parameters[0] = 99;
        '''
        result = extract(source, 'action', 4)
        self.assertEqual(result['holes'], [0, 2])
        self.assertEqual(result['templates'][0]['name'], 'FINAL')
        self.assertEqual(result['templates'][0]['argument_types'], [4])
        self.assertEqual(result['templates'][1]['argument_types'], [None])
        self.assertEqual(extract(source, 'condition', 4)['templates'][0]['name'], 'OTHER')
        with self.assertRaisesRegex(ValueError, 'Unsupported relevant'):
            extract(source.replace('m_numParameters = 1;', 'm_numParameters = UNKNOWN;'), 'action', 4)

    def catalog(self):
        return dict(schema=1, game='BFME2 1.06', condition=dict(templates=[
            dict(opcode=3, name='CONDITION_TRUE', argument_types=[])]),
            action=dict(templates=[dict(opcode=2, name='SET_COUNTER', argument_types=[4, 0]),
                                   dict(opcode=999, name='UNRESOLVED', argument_types=[None])]))

    def test_author_install_and_decode_original_script(self):
        m = create(64, 64, 4)
        writer = Writer(m, self.catalog())
        condition = writer.operation('condition', 'CONDITION_TRUE')
        action = writer.operation('action', 'SET_COUNTER', [arg(4, text='Score'), arg(0, integer=8)])
        writer.install([writer.script('Original', [[condition]], [action])])
        report = inventory(player_scripts(Map(m.encode())))
        self.assertTrue(report['payloads_decoded'])
        self.assertEqual(report['versions']['Script v4'], 1)
        self.assertEqual(report['signatures'][1]['argument_types'], (4, 0))
        with self.assertRaisesRegex(ValueError, 'empty'):
            writer.install([])

    def test_wrong_or_unknown_arguments_are_rejected(self):
        w = Writer(create(64, 64, 4), self.catalog())
        with self.assertRaisesRegex(ValueError, 'expects'):
            w.operation('action', 'SET_COUNTER', [arg(0), arg(4)])
        with self.assertRaisesRegex(ValueError, 'Unresolved'):
            w.operation('action', 'UNRESOLVED', [arg(0)])
        with self.assertRaises(ValueError):
            arg(16, position=(0, float('nan'), 0))
        with self.assertRaises(ValueError):
            arg(0, integer=2**32)

    def test_catalog_compare_does_not_normalize_mismatch(self):
        audit = dict(signatures=[dict(chunk='ScriptAction', opcode_raw=2,
            internal_name='SET_COUNTER', argument_types=[4, 1])])
        self.assertEqual(len(compare(self.catalog(), audit)['mismatches']), 1)

    def test_native_defaults_only_fill_unknowns(self):
        source = dict(action=dict(slots=2, templates=[dict(opcode=0, name='ZERO', argument_types=None),
            dict(opcode=1, name='ONE', argument_types=[None, 4])]),
            condition=dict(slots=1, templates=[]))
        live = dict(evidence='Live BFME2 1.06 template memory', action=[
            dict(opcode=0, name='ZERO', argument_types=[]),
            dict(opcode=1, name='ONE', argument_types=[0, 4])],
            condition=[dict(opcode=0, name='', argument_types=[])])
        result = reconcile(source, live)
        self.assertEqual(result['action']['templates'][1]['argument_types'], [0, 4])
        self.assertIsNone(source['action']['templates'][0]['argument_types'])
        self.assertEqual(len(result['native_reconciliation']['resolved_defaults']), 2)
        live['action'][1]['argument_types'] = [0, 7]
        with self.assertRaisesRegex(ValueError, 'disagrees'):
            reconcile(source, live)


if __name__ == '__main__':
    unittest.main()
