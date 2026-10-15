"""Independent fixture checks for sandbox isolation, replay and repeated results."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from quality_ops import COLUMNS, analyse, write_csv
from qualitylab import EDITABLE, Laboratory


def fixture(root):
    inputs = root / 'inputs'
    inputs.mkdir()
    data = {
        'batches': [['B1', 'Demo tablet', '2026-01-01']],
        'test_results': [
            ['T1', 'B1', 'assay', 'demo-HPLC', 90, '%', 95, 105, '%', '2026-01-02'],
            ['T2', 'B1', 'assay', 'demo-HPLC', None, '%', 95, 105, '%', '2026-01-02'],
            ['T3', 'B1', 'assay', 'demo-HPLC', 100, '%', 95, 105, '%', '2026-07-02']],
        'deviations': [], 'actions': [],
    }
    for table, columns in COLUMNS.items():
        write_csv(inputs / (table + '.csv'), columns, data[table])
    (inputs / 'SOURCE.json').write_text(json.dumps({'data_type': 'synthetic'}), encoding='utf-8')
    result = analyse(inputs, root / 'analysis', '2026-06-30')
    return inputs, result


class LaboratoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs, self.baseline = fixture(self.root)
        self.database = self.root / 'analysis/quality.sqlite'
        self.before = self.database.read_bytes()
        self.model = Laboratory(self.database, '2026-06-30', self.baseline['artifact_sha256']['quality.sqlite'])

    def test_unchanged_scenario_and_source_bytes(self):
        result = self.model.run('2026-06-30')
        self.assertEqual(result['baseline_metrics'], self.baseline['metrics'])
        self.assertTrue(all(row['delta'] == 0 for row in result['metrics']))
        self.assertEqual(result['baseline_metrics']['outside_range_records'], 1)
        self.assertEqual(result['baseline_metrics']['missing_records'], 1)
        self.assertEqual(result['transitions'], [])
        self.assertEqual(self.database.read_bytes(), self.before)

    def test_result_edits_do_not_invent_deviations_or_replace_baseline(self):
        self.model.stage('T1', {'value': '100'})
        result = self.model.run('2026-06-30')
        self.assertEqual(result['baseline_metrics']['outside_range_records'], 1)
        self.assertEqual(result['scenario_metrics']['outside_range_records'], 0)
        self.assertEqual(result['scenario_metrics']['open_deviations'], 0)
        self.assertEqual(result['transitions'][0]['baseline_value'], 90)
        self.assertEqual(result['transitions'][0]['after_status'], 'within_range')
        self.assertEqual(self.database.read_bytes(), self.before)

    def test_zero_and_missing_are_distinct_and_boundaries_are_inclusive(self):
        self.model.stage('T2', {'value': '0'})
        result = self.model.run('2026-06-30')
        self.assertEqual(result['scenario_metrics']['missing_records'], 0)
        self.assertEqual(result['scenario_metrics']['outside_range_records'], 2)
        self.model.stage('T1', {'value': '95'})
        self.assertEqual(self.model.run('2026-06-30')['scenario_metrics']['outside_range_records'], 1)
        self.model.stage('T1', {'value': '105'})
        self.assertEqual(self.model.run('2026-06-30')['scenario_metrics']['outside_range_records'], 1)
        self.model.stage('T2', {'value': ''})
        self.assertNotIn('T2', self.model.changes)

    def test_date_edit_explains_a_changed_denominator(self):
        self.model.stage('T1', {'measured_on': '2026-07-01'})
        result = self.model.run('2026-06-30')
        self.assertEqual(result['baseline_metrics']['measured_records'], 2)
        self.assertEqual(result['scenario_metrics']['measured_records'], 1)
        self.assertEqual(result['transitions'][0]['after_status'], 'not_measured')
        self.assertEqual(result['as_of'], '2026-06-30')
        self.assertEqual(self.model.run('2026-07-31')['scenario_metrics']['measured_records'], 3)

    def test_hypothetical_bound_edit_is_explicit(self):
        self.model.stage('T1', {'spec_low': 85})
        result = self.model.run('2026-06-30')
        self.assertEqual(result['transitions'][0]['baseline_low'], 95)
        self.assertEqual(result['transitions'][0]['scenario_low'], 85)
        self.assertEqual(result['scenario_metrics']['outside_range_records'], 0)
        self.assertIn('hypothetical', result['scope'])

    def test_invalid_edits_are_atomic(self):
        self.model.stage('T1', {'value': 100})
        original = deepcopy(self.model.changes)
        for patch in ({'value': 'NaN'}, {'value': 'inf'}, {'value': True}, {'spec_low': ''},
                      {'value': 99, 'spec_low': 110}, {'measured_on': '2025-12-31'},
                      {'measured_on': '2026-02-30'}, {'unit': 'mg'}):
            with self.subTest(patch=patch):
                with self.assertRaises(ValueError):
                    self.model.stage('T1', patch)
                self.assertEqual(self.model.changes, original)
        with self.assertRaises(ValueError):
            self.model.stage('unknown', {'value': 100})

    def test_reset_and_snapshot_capture_do_not_depend_on_mutable_files(self):
        self.model.stage('T1', {'value': 100})
        self.database.write_bytes(b'changed after opening')
        self.assertEqual(self.model.run('2026-06-30')['scenario_metrics']['outside_range_records'], 0)
        self.model.reset()
        self.assertTrue(all(row['delta'] == 0 for row in self.model.run('2026-06-30')['metrics']))
        with self.assertRaisesRegex(ValueError, 'differs'):
            Laboratory(self.database, '2026-06-30', self.baseline['artifact_sha256']['quality.sqlite'])

    def test_returned_rows_cannot_mutate_the_baseline(self):
        rows = self.model.tests
        rows[0]['value'] = 999
        self.assertEqual(self.model.current('T1')['value'], 90)

    def plan(self, value=100, low=95, high=105, date='2026-01-03'):
        return dict(zip(EDITABLE, [value, low, high, date]))

    def test_original_outside_result_survives_two_later_inside_results(self):
        exercise = self.model.recheck('T1', [self.plan(), self.plan(low=98, high=102, date='2026-01-04')], 'Preset training exercise')
        self.assertEqual([row['snapshot_status'] for row in exercise['attempts']],
                         ['outside_range', 'within_range', 'within_range'])
        self.assertTrue(exercise['any_outside_range'])
        self.assertEqual(exercise['original_status'], 'outside_range')
        self.assertEqual(self.model.changes, {})
        self.assertNotIn('accepted', exercise)
        self.assertEqual(self.database.read_bytes(), self.before)

    def test_recheck_rejects_widening_backdated_or_unplanned_attempts(self):
        for plans, reason in [([self.plan(low=90)], 'Reason'), ([self.plan(date='2026-01-01')], 'Reason'),
                              ([{'value': 100}], 'Reason'), ([self.plan()], ''), ([], 'Reason'),
                              ([self.plan()] * 3, 'Reason')]:
            with self.subTest(plans=plans, reason=reason):
                with self.assertRaises(ValueError):
                    self.model.recheck('T1', plans, reason)

    def test_export_replays_both_arms_and_preserves_all_attempts(self):
        self.model.stage('T1', {'value': 100})
        result = self.model.run('2026-06-30')
        result['rechecks'] = [self.model.recheck('T1', [self.plan()], 'Training <script>not markup</script>')]
        destination = self.model.export(result, self.root / 'experiment')
        baseline = analyse(destination / 'baseline', self.root / 'replay-baseline', result['as_of'])
        scenario = analyse(destination / 'scenario', self.root / 'replay-scenario', result['as_of'])
        self.assertEqual(baseline['metrics'], result['baseline_metrics'])
        self.assertEqual(scenario['metrics'], result['scenario_metrics'])
        manifest = json.loads((destination / 'manifest.json').read_text())
        self.assertTrue(manifest['complete'])
        for name, digest in manifest['artifacts'].items():
            self.assertEqual(hashlib.sha256((destination / name).read_bytes()).hexdigest(), digest)
        report = (destination / 'LAB.en.html').read_text(encoding='utf-8')
        self.assertIn('&lt;script&gt;', report)
        self.assertNotIn('<script>', report)
        self.assertTrue((destination / 'recheck_attempts.csv').exists())
        with self.assertRaises(FileExistsError):
            self.model.export(result, destination)

    def test_export_frozen_result_does_not_substitute_newer_edits(self):
        self.model.stage('T1', {'value': 100})
        result = self.model.run('2026-06-30')
        self.model.stage('T1', {'value': 999})
        self.model.export(result, self.root / 'old-run')
        stored = json.loads((self.root / 'old-run/EXPERIMENT.json').read_text(encoding='utf-8'))
        self.assertEqual(stored['changes']['T1']['value'], 100)

    def test_tampered_result_is_rejected_before_any_export(self):
        result = self.model.run('2026-06-30')
        result['scenario_metrics']['outside_range_records'] = 99
        with self.assertRaises(ValueError):
            self.model.export(result, self.root / 'tampered')
        self.assertFalse((self.root / 'tampered').exists())


if __name__ == '__main__':
    unittest.main()
