import unittest

from formats.map import Map
from formats.scripts import inventory, player_scripts
from mapkit.blank import create
from mapkit.script_catalog import extract, compare, reconcile
from mapkit.script_writer import Writer, arg


class ScriptAuthoringTests(unittest.TestCase):
    def test_bundled_catalog_supports_clean_checkout_authoring(self):
        from mapkit.script_catalog import load_catalog
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

    def test_nested_groups_and_execution_fields_round_trip(self):
        m = create(64, 64, 4)
        w = Writer(m, self.catalog())
        leaf = w.script('Leaf', [[w.operation('condition','CONDITION_TRUE')]], [],
            easy=False, medium=True, hard=False, sequential=True, loop=True,
            loop_count=-1, target_type_raw=255, target_name='Target', player_mask_text='RAW',
            comment='Notes', conditions_comment='When', actions_comment='Then', interval=17)
        w.install([w.group('Outer', [w.group('Inner', [leaf], subroutine=True)], active=False)])
        tree = player_scripts(Map(m.encode()))[0]['children'][0]
        self.assertEqual((tree['name'], tree['active_raw']), ('Outer', 0))
        inner = tree['children'][0]
        self.assertEqual(inner['subroutine_raw'], 1)
        script = inner['children'][0]
        self.assertEqual([script[k] for k in ('easy_raw','medium_raw','hard_raw','sequential_raw','loop_raw')], [0,1,0,1,1])
        self.assertEqual([script[k] for k in ('loop_count','target_type_raw','target_name','player_mask_text')], [-1,255,'Target','RAW'])
        self.assertEqual(script['actions_comment'], 'Then')
        self.assertEqual(script['evaluation_interval_raw'],17)
        with self.assertRaisesRegex(ValueError,'empty'):
            w.install([])

    def test_execution_writer_rejects_invalid_children_and_widths(self):
        w = Writer(create(64,64,4), self.catalog())
        cond = w.operation('condition','CONDITION_TRUE')
        for settings in ({'loop_count':2**31}, {'target_type_raw':256}, {'easy':2}):
            with self.assertRaises(ValueError): w.script('Bad', [[cond]], [], **settings)
        with self.assertRaisesRegex(ValueError,'Expected Script'):
            w.group('Bad', [cond])
        item = w.script('Leaf', [[cond]], [])
        with self.assertRaisesRegex(ValueError,'nesting'):
            for i in range(65): item = w.group('Level'+str(i), [item])

    def test_original_execution_lab_is_fully_decoded(self):
        from mapkit.script_lab import build
        m, proof = build(execution_probe=True)
        report = inventory(player_scripts(Map(m.encode())))
        self.assertTrue(report['payloads_decoded'])
        self.assertEqual(report['versions']['ScriptGroup v3'],8)
        self.assertIn('LAB_CalledSubroutine', proof['expected'])
        self.assertIn('LAB_ForbiddenInactiveParent', proof['forbidden'])
        self.assertEqual(len(proof['one_of'][0]),3)

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
