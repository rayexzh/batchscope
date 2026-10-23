"""Save, close and restore regressions using actual desktop controls."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch

from app import Window
from lab_session import save_session, load_session
from test_qualitylab import fixture


class ProgressWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        _, result = fixture(self.folder)
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.app = Window(self.root)
        self.app.result, self.app.output, self.app.phase = result, self.folder/'analysis', 'completed'
        self.view = self.app.open_laboratory()
        self.view.window.withdraw()
        self.path = self.folder/'saved.bslab'

    def save(self):
        with patch('qualitylab_ui.filedialog.asksaveasfilename', return_value=str(self.path)):
            self.view.save_work()
        self.assertTrue(self.path.is_file())

    def resume(self):
        with patch('app.filedialog.askopenfilename', return_value=str(self.path)):
            view = self.app.open_lab_progress()
        self.assertIsNotNone(view)
        view.window.withdraw()
        return view

    def evaluate(self):
        self.view.buttons['evaluate'].invoke()
        deadline = time.monotonic()+8
        while self.view.busy and time.monotonic()<deadline:
            self.root.update()
            time.sleep(.01)
        self.assertFalse(self.view.busy)

    def test_saved_draft_closes_without_discard_warning_new_edit_still_warns(self):
        self.view.fields['value'].set('unfinished')
        self.save()
        with patch('qualitylab_ui.messagebox.askyesno', return_value=False) as ask:
            self.assertTrue(self.view.confirm_close())
            ask.assert_not_called()
            self.view.fields['value'].set('different unfinished')
            self.assertFalse(self.view.confirm_close())
            ask.assert_called_once()
        resumed = self.resume()
        self.assertEqual(resumed.fields['value'].get(), 'unfinished')
        with patch('qualitylab_ui.messagebox.askyesno') as ask:
            self.assertTrue(resumed.confirm_close())
            ask.assert_not_called()
        resumed.as_of.set('2026-07-31')
        with patch('qualitylab_ui.messagebox.askyesno', return_value=False):
            self.assertFalse(resumed.confirm_close())

    def test_two_attempt_plan_keeps_whitespace_and_unused_third_fields(self):
        self.view.reason.set('  Planned exercise  ')
        self.view.repeat_fields[0]['value'].set(' 100.00 ')
        self.view.repeat_fields[1]['value'].set('unused draft')
        self.view.round_count.set('2')
        self.evaluate()
        self.assertFalse(any(self.view.pending()))
        self.save()
        resumed = self.resume()
        self.assertFalse(any(resumed.pending()))
        self.assertEqual(resumed.reason.get(), '  Planned exercise  ')
        self.assertEqual(resumed.repeat_fields[1]['value'].get(), 'unused draft')
        self.assertEqual(len(resumed.rechecks[0]['attempts']), 2)
        resumed.run()
        deadline = time.monotonic()+8
        while resumed.busy and time.monotonic()<deadline:
            self.root.update();time.sleep(.01)
        self.assertTrue(resumed.buttons['export'].instate(['!disabled']))
        resumed.repeat_fields[0]['value'].set('101')
        self.assertTrue(resumed.buttons['export'].instate(['disabled']))
        # Previous alpha progress files have no evaluated_plans field.
        payload = json.loads(self.path.read_text(encoding='utf-8'))
        payload['state'].pop('evaluated_plans')
        self.path.write_text(json.dumps(payload), encoding='utf-8')
        legacy = self.resume()
        self.assertFalse(any(legacy.pending()))

    def test_interrupted_save_publishes_no_partial_file_or_checkpoint(self):
        self.view.fields['value'].set('101')
        with patch('lab_session.os.fsync', side_effect=OSError('Simulated interrupted write')):
            with patch('qualitylab_ui.filedialog.asksaveasfilename', return_value=str(self.path)), patch('qualitylab_ui.messagebox.showerror') as error:
                self.view.save_work()
                error.assert_called_once()
        self.assertFalse(self.path.exists())
        self.assertEqual(list(self.folder.glob('.batchscope-*')), [])
        self.assertIsNone(self.view.saved_progress)

    def test_existing_copy_is_preserved(self):
        self.save()
        before = self.path.read_bytes()
        self.view.fields['value'].set('102')
        with patch('qualitylab_ui.filedialog.asksaveasfilename', return_value=str(self.path)), patch('qualitylab_ui.messagebox.showerror') as error:
            self.view.save_work()
            error.assert_called_once()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.folder.glob('.batchscope-*')), [])

    def test_invalid_draft_shape_is_rejected_before_writing(self):
        state = deepcopy(self.view.progress_state())
        state['forms'][self.view.selected_id]['main']['value'] = 'x'*4097
        with self.assertRaises(ValueError):
            save_session(self.path, self.view.model, state)
        self.assertFalse(self.path.exists())

    def test_duplicate_json_fields_and_altered_evaluation_are_rejected(self):
        self.save()
        payload = self.path.read_text(encoding='utf-8')
        self.path.write_text(payload.replace('"format": 1', '"format": 1, "format": 1'), encoding='utf-8')
        with self.assertRaises(ValueError):
            load_session(self.path)
        self.path.write_text(payload.replace('"format": 1', '"format": NaN'), encoding='utf-8')
        with self.assertRaises(ValueError):
            load_session(self.path)
        state = deepcopy(self.view.progress_state())
        state['evaluated_plans'] = {'T1': self.view.default_plan('T1')}
        with self.assertRaises(ValueError):
            save_session(self.folder/'invalid-evaluation.bslab', self.view.model, state)
