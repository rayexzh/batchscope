"""Boundary and portable-progress regression checks."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from lab_session import save_session, load_session
from quality_ops import analyse, COLUMNS, write_csv
from test_qualitylab import fixture
from qualitylab import Laboratory


class ExactProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs, self.result = fixture(self.root)
        self.model = Laboratory(self.root/'analysis/quality.sqlite', '2026-06-30',
                                self.result['artifact_sha256']['quality.sqlite'])

    def test_boundary_and_export_replay_keep_every_digit(self):
        for value in ('94.999999999999999', '105.000000000000001', '-0.000000000000000001'):
            with self.subTest(value=value):
                self.model.stage('T1', {'value': value})
                result = self.model.run('2026-06-30')
                self.assertEqual(result['transitions'][0]['after_status'], 'outside_range')
                self.assertEqual(str(self.model.current('T1')['value']), value)
        self.model.stage('T1', {'value': '94.999999999999999'})
        result = self.model.run('2026-06-30')
        target = self.root/'export'
        self.model.export(result, target)
        replay = analyse(target/'scenario', self.root/'replay', '2026-06-30')
        self.assertEqual(replay['metrics'], result['scenario_metrics'])
        self.assertIn('94.999999999999999', (target/'scenario/test_results.csv').read_text(encoding='utf-8-sig'))
        repeat = self.model.recheck('T1', [{'value': '94.999999999999999', 'spec_low': '95',
            'spec_high': '105', 'measured_on': '2026-01-03'}], 'Boundary check')
        self.assertEqual(repeat['attempts'][1]['snapshot_status'], 'outside_range')
        with self.assertRaises(ValueError):
            self.model.stage('T1', {'spec_low': '105.000000000000001', 'spec_high': '105'})

    def state(self):
        return {'as_of': '2026-06-30', 'selected_id': 'T2', 'rechecks': [],
            'forms': {'T2': {'main': {'value': 'unfinished.', 'spec_low': '95', 'spec_high': '105', 'measured_on': '2026-01-02'},
                'repeat': {'rounds': '2', 'reason': 'Pending exercise', 'fields': [
                    {'value': '', 'spec_low': '95', 'spec_high': '105', 'measured_on': '2026-01-03'} for _ in range(2)]}}}}

    def test_resume_without_source_and_reject_corruption(self):
        self.model.stage('T1', {'value': '100.0000'})
        path = self.root/'progress.bslab'
        state = self.state()
        save_session(path, self.model, state)
        with self.assertRaises(FileExistsError):
            save_session(path, self.model, state)
        shutil.rmtree(self.root/'analysis')
        model, restored = load_session(path)
        self.assertEqual(str(model.current('T1')['value']), '100.0000')
        self.assertEqual(restored, state)
        self.assertEqual(model.run(state['as_of'])['scenario_metrics']['outside_range_records'], 0)
        payload = json.loads(path.read_text(encoding='utf-8'))
        payload['sha256'] = '0'*64
        path.write_text(json.dumps(payload), encoding='utf-8')
        with self.assertRaises(ValueError):
            load_session(path)

    def test_ui_resume_keeps_invalid_draft_and_export_blocked(self):
        import tkinter as tk
        from app import Window, RecordTable
        from qualitylab_ui import LaboratoryWindow
        root = tk.Tk()
        root.withdraw()
        try:
            owner = Window(root)
            view = LaboratoryWindow(owner, RecordTable, None, self.model.as_of, self.model.source_sha256, model=self.model)
            view.window.withdraw()
            view.restore_progress(self.state())
            self.assertEqual(view.selected_id, 'T2')
            self.assertEqual(view.fields['value'].get(), 'unfinished.')
            self.assertIn('T2', view.pending()[0])
            self.assertTrue(view.buttons['export'].instate(['disabled']))
        finally:
            root.destroy()
