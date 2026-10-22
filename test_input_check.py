"""Check malformed inputs, preserved missing/repeat rows and captured-byte provenance."""
from contextlib import closing
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import quality_ops
from input_check_ui import export_check
from quality_ops import analyse, check_inputs, finite_number, input_report
from qualitylab import Laboratory
from test_qualitylab import fixture


class InputCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs, self.baseline = fixture(self.root)

    def rewrite_tests(self, change):
        path = self.inputs / 'test_results.csv'
        with path.open(encoding='utf-8-sig', newline='') as handle:
            rows = list(csv.reader(handle))
        change(rows)
        with path.open('w', encoding='utf-8-sig', newline='') as handle:
            csv.writer(handle).writerows(rows)

    def test_supplied_example_has_two_review_prompts_without_changing_analysis(self):
        inputs = Path(__file__).parent / 'examples/range-differences'
        checked = check_inputs(inputs)
        self.assertEqual(checked['counts'], {'error': 0, 'warning': 2, 'info': 0})
        self.assertTrue(checked['can_analyse'])
        result = analyse(inputs, self.root / 'supplied-example', '2026-06-30')
        self.assertEqual(result['metrics']['measured_records'], 3)
        self.assertEqual(result['metrics']['outside_range_records'], 0)

    def test_orphan_findings_name_the_real_column_and_entered_identifier(self):
        import shutil
        for table, columns, row, field, target in [
            ('test_results', quality_ops.COLUMNS['test_results'],
             ['X', 'NOT-FOUND', 'assay', 'demo', 100, '%', 95, 105, '%', '2026-01-02'], 'batch_id', 'batches.csv'),
            ('deviations', quality_ops.COLUMNS['deviations'],
             ['D1', 'NOT-FOUND', 'demo', '2026-01-02', ''], 'batch_id', 'batches.csv'),
            ('actions', quality_ops.COLUMNS['actions'],
             ['A1', 'NOT-FOUND', 'QC', '2026-01-02', '2026-01-03', ''], 'deviation_id', 'deviations.csv')]:
            source = self.root / ('orphan-' + table)
            shutil.copytree(self.inputs, source)
            with (source / (table + '.csv')).open('w', encoding='utf-8-sig', newline='') as handle:
                writer = csv.writer(handle);writer.writerow(columns);writer.writerow(row)
            checked = check_inputs(source)
            self.assertFalse(checked['can_analyse'])
            finding = next(r for r in checked['findings'] if target in r['reason'])
            self.assertEqual((finding['table'], finding['row'], finding['field'], finding['value']),
                             (table, 2, field, 'NOT-FOUND'))

    def test_read_only_check_retains_missing_and_future_records(self):
        before = {p.name: p.read_bytes() for p in self.inputs.iterdir()}
        result = check_inputs(self.inputs)
        self.assertTrue(result['can_analyse'])
        self.assertEqual(result['counts'], {'error': 0, 'warning': 0, 'info': 1})
        self.assertEqual(result['profiles'][1]['readable_records'], 3)
        self.assertEqual(result['findings'][0]['row'], 3)
        self.assertEqual(result['findings'][0]['level'], 'info')
        self.assertEqual({p.name: p.read_bytes() for p in self.inputs.iterdir()}, before)
        self.assertEqual(result['input_sha256'], {k: hashlib.sha256(v).hexdigest() for k, v in before.items()})
        self.assertNotIn('_data', input_report(result))

    def test_missing_files_are_all_listed_and_never_create_database(self):
        missing = self.root / 'empty'
        missing.mkdir()
        result = check_inputs(missing)
        self.assertFalse(result['can_analyse'])
        self.assertEqual(result['counts']['error'], 5)
        self.assertEqual({r['table'] for r in result['findings']},
                         {'SOURCE.json', 'batches', 'test_results', 'deviations', 'actions'})
        self.assertEqual(list(missing.iterdir()), [])
        with self.assertRaises(ValueError):
            analyse(missing, self.root / 'stopped', '2026-06-30')
        self.assertFalse((self.root / 'stopped').exists())

    def test_numeric_notation_is_explicit_in_both_import_and_laboratory(self):
        model = Laboratory(self.root / 'analysis/quality.sqlite', '2026-06-30',
                           self.baseline['artifact_sha256']['quality.sqlite'])
        for text in ('1_00', '98%', '1,2', 'NaN', 'inf', '1e999', '=100'):
            with self.subTest(value=text):
                self.rewrite_tests(lambda rows: rows[1].__setitem__(4, text))
                result = check_inputs(self.inputs)
                found = [r for r in result['findings'] if r['level'] == 'error']
                self.assertFalse(result['can_analyse'])
                self.assertEqual([(r['row'], r['field'], r['value']) for r in found], [(2, 'value', text)])
                with self.assertRaises(ValueError):
                    model.stage('T1', {'value': text})
                self.assertEqual(model.changes, {})
        for text, expected in (('0', 0), ('-1.25', -1.25), ('+1.0e2', 100), ('.5', .5)):
            self.assertEqual(finite_number(text), expected)
        with self.assertRaises(ValueError):
            finite_number(True)

    def test_blocking_check_exports_findings_before_analysis_stops(self):
        self.rewrite_tests(lambda rows: rows[1].__setitem__(4, '98%'))
        output = self.root / 'invalid-analysis'
        with self.assertRaises(ValueError):
            analyse(self.inputs, output, '2026-06-30')
        self.assertTrue((output / 'INPUT_CHECK.json').is_file())
        self.assertTrue((output / 'INPUT_FINDINGS.csv').is_file())
        self.assertFalse((output / 'quality.sqlite').exists())
        self.assertFalse((output / 'manifest.json').exists())

    def test_matching_content_warns_but_retains_each_numbered_record(self):
        def append(rows):
            rows.append(['T4'] + rows[1][1:])
            rows.append(['T5'] + rows[1][1:])
            rows[-1][-1] = '2026-01-03'  # Same value on another date is not an exact match.
        self.rewrite_tests(append)
        result = check_inputs(self.inputs)
        warnings = [r for r in result['findings'] if r['level'] == 'warning']
        self.assertTrue(result['can_analyse'])
        self.assertEqual([(r['row'], r['related_row'], r['value']) for r in warnings], [(5, 2, 'T4')])
        final = analyse(self.inputs, self.root / 'with-repeat', '2026-06-30')
        self.assertEqual(final['metrics']['measured_records'], 4)
        self.assertEqual(final['metrics']['outside_range_records'], 3)
        with closing(sqlite3.connect(self.root / 'with-repeat/quality.sqlite')) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM test_results').fetchone()[0], 5)

    def test_duplicate_identifier_still_blocks_and_unit_errors_are_specific(self):
        self.rewrite_tests(lambda rows: rows.append(list(rows[1])))
        result = check_inputs(self.inputs)
        self.assertFalse(result['can_analyse'])
        self.assertTrue(any(r['reason'] == 'Duplicate primary key.' for r in result['findings']))
        self.rewrite_tests(lambda rows: rows.pop())
        self.rewrite_tests(lambda rows: rows[1].__setitem__(5, 'mg'))
        result = check_inputs(self.inputs)
        self.assertTrue(any(r['field'] == 'unit' and r['value'] == 'mg' for r in result['findings']))

    def test_analysis_uses_the_same_bytes_as_its_recorded_input_hashes(self):
        path = self.inputs / 'test_results.csv'
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        loader = quality_ops.load_inputs
        def mutate_after_capture(*args, **kwargs):
            loaded = loader(*args, **kwargs)
            self.rewrite_tests(lambda rows: rows[1].__setitem__(4, '100'))
            return loaded
        with patch('quality_ops.load_inputs', side_effect=mutate_after_capture):
            result = analyse(self.inputs, self.root / 'captured', '2026-06-30')
        self.assertEqual(result['input_sha256']['test_results.csv'], digest)
        self.assertNotEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
        with closing(sqlite3.connect(self.root / 'captured/quality.sqlite')) as db:
            self.assertEqual(db.execute("SELECT value FROM test_results WHERE test_id='T1'").fetchone()[0], '90')
        check = json.loads((self.root / 'captured/INPUT_CHECK.json').read_text(encoding='utf-8'))
        self.assertEqual(check['input_sha256'], result['input_sha256'])

    def test_source_marker_with_bom_and_non_synthetic_marker(self):
        marker = self.inputs / 'SOURCE.json'
        marker.write_text('{"data_type":"synthetic"}', encoding='utf-8-sig')
        self.assertTrue(check_inputs(self.inputs)['can_analyse'])
        marker.write_text('{"data_type":"real"}', encoding='utf-8')
        self.assertFalse(check_inputs(self.inputs)['can_analyse'])
        with self.assertRaises(ValueError):
            analyse(self.inputs, self.root / 'real', '2026-06-30')
        self.assertFalse((self.root / 'real').exists())

    def test_nonzero_underflow_stops_import_and_laboratory_without_becoming_zero(self):
        model = Laboratory(self.root / 'analysis/quality.sqlite', '2026-06-30',
                           self.baseline['artifact_sha256']['quality.sqlite'])
        for value in ('1e-999', '-1e-999', '1e-9999999999999999999999999999999999'):
            with self.subTest(value=value):
                self.rewrite_tests(lambda rows: rows[1].__setitem__(4, value))
                result = check_inputs(self.inputs)
                self.assertFalse(result['can_analyse'])
                error = next(r for r in result['findings'] if r['level'] == 'error')
                self.assertEqual(error['value'], value)
                self.assertIn('would become zero', error['reason'])
                with self.assertRaisesRegex(ValueError, 'would become zero'):
                    model.stage('T1', {'value': value})
                self.assertEqual(model.changes, {})
        for value in ('0', '-0.0', '0e-9999999999999999999999999999999999'):
            self.assertEqual(finite_number(value), 0)
        self.assertGreater(finite_number('5e-324'), 0)

    def test_zero_result_cannot_pass_a_lower_bound_that_underflows_to_zero(self):
        def change(rows):
            rows[1][4], rows[1][6] = '0', '1e-999'
        self.rewrite_tests(change)
        result = check_inputs(self.inputs)
        self.assertFalse(result['can_analyse'])
        found = [r for r in result['findings'] if r['level'] == 'error']
        self.assertEqual([(r['row'], r['field'], r['value']) for r in found], [(2, 'spec_low', '1e-999')])
        with self.assertRaises(ValueError):
            analyse(self.inputs, self.root / 'underflow-bound', '2026-06-30')
        self.assertFalse((self.root / 'underflow-bound/quality.sqlite').exists())

    def test_different_ranges_flag_both_sides_without_choosing_an_approved_one(self):
        self.rewrite_tests(lambda rows: rows[2].__setitem__(6, '85'))
        before = (self.inputs / 'test_results.csv').read_bytes()
        result = check_inputs(self.inputs)
        found = [r for r in result['findings'] if r['field'] == 'spec_low/spec_high']
        self.assertTrue(result['can_analyse'])
        self.assertEqual({r['row'] for r in found}, {2, 3, 4})
        self.assertEqual({(r['row'], r['related_row']) for r in found}, {(2, 3), (3, 2), (4, 3)})
        self.assertEqual(found[0]['value'], '95 .. 105')
        self.assertEqual(found[0]['reference_value'], '85 .. 105')
        final = analyse(self.inputs, self.root / 'different-ranges', '2026-06-30')
        self.assertEqual(final['metrics'], self.baseline['metrics'])
        self.assertEqual((self.inputs / 'test_results.csv').read_bytes(), before)
        exported = export_check(input_report(result), self.root / 'ranges-export')
        with (exported / 'INPUT_FINDINGS.csv').open(encoding='utf-8-sig', newline='') as handle:
            rows = list(csv.DictReader(handle))
        comparisons = [r for r in rows if r['field'] == 'spec_low/spec_high']
        self.assertEqual(len(comparisons), 3)
        self.assertTrue(all(r['reference_value'] for r in comparisons))
        body = (exported / 'INPUT_CHECK.en.html').read_text(encoding='utf-8')
        self.assertIn('not approved', body)
        self.assertIn('85 .. 105', body)

    def test_range_comparisons_never_mix_different_methods_tests_units_or_products(self):
        for field, replacement in ((2, 'purity'), (3, 'another-method'), (5, 'mg')):
            with self.subTest(field=field):
                original = (self.inputs / 'test_results.csv').read_bytes()
                def change(rows):
                    rows[2][6] = '85'
                    rows[2][field] = replacement
                    if field == 5:
                        rows[2][8] = replacement
                self.rewrite_tests(change)
                result = check_inputs(self.inputs)
                self.assertTrue(result['can_analyse'])
                self.assertFalse(any(r['field'] == 'spec_low/spec_high' for r in result['findings']))
                (self.inputs / 'test_results.csv').write_bytes(original)
        batch_path = self.inputs / 'batches.csv'
        with batch_path.open('a', encoding='utf-8', newline='') as handle:
            csv.writer(handle).writerow(['B2', 'Different product', '2026-01-01'])
        def different_product(rows):
            rows[2][1], rows[2][6] = 'B2', '85'
        self.rewrite_tests(different_product)
        self.assertFalse(any(r['field'] == 'spec_low/spec_high' for r in check_inputs(self.inputs)['findings']))
        batch_path.write_text(batch_path.read_text(encoding='utf-8-sig').replace('Different product', 'Demo tablet'),
                              encoding='utf-8-sig')
        self.assertEqual(sum(r['field'] == 'spec_low/spec_high' for r in check_inputs(self.inputs)['findings']), 3)

    def test_range_comparison_is_symmetric_with_three_ranges_and_skips_invalid_inputs(self):
        def three_ranges(rows):
            rows[2][6], rows[3][6] = '85', '75'
        self.rewrite_tests(three_ranges)
        result = check_inputs(self.inputs)
        found = [r for r in result['findings'] if r['field'] == 'spec_low/spec_high']
        self.assertEqual(len(found), 3)
        self.assertTrue(all(r['value'] != r['reference_value'] for r in found))
        self.rewrite_tests(lambda rows: rows[1].__setitem__(4, 'not a number'))
        result = check_inputs(self.inputs)
        self.assertFalse(result['can_analyse'])
        self.assertFalse(any(r['field'] == 'spec_low/spec_high' for r in result['findings']))

    def test_export_escapes_text_preserves_all_findings_and_refuses_overwrite(self):
        self.rewrite_tests(lambda rows: rows[1].__setitem__(4, '<script>alert(1)</script>'))
        result = input_report(check_inputs(self.inputs))
        output = export_check(result, self.root / 'export')
        saved = json.loads((output / 'INPUT_CHECK.json').read_text(encoding='utf-8'))
        self.assertEqual(saved['findings'], result['findings'])
        self.assertNotIn('_data', saved)
        for name in ('INPUT_CHECK.en.html', 'INPUT_CHECK.zh-CN.html'):
            body = (output / name).read_text(encoding='utf-8')
            self.assertIn('&lt;script&gt;', body)
            self.assertNotIn('<script>', body)
        manifest = json.loads((output / 'manifest.json').read_text())
        self.assertTrue(manifest['complete'])
        for name, expected in manifest['artifacts'].items():
            self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), expected)
        with self.assertRaises(FileExistsError):
            export_check(result, output)


if __name__ == '__main__':
    unittest.main()
