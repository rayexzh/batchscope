"""Regressions for the observed QC draft, export and minimum-window failures."""
import gc
import json
from pathlib import Path
import tempfile
import threading
import time
import tkinter as tk
import unittest
from unittest.mock import patch

from app import Window
from test_qualitylab import fixture


class QcWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.inputs, self.result = fixture(self.folder)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = Window(self.root)
        self.app.result, self.app.output, self.app.phase = self.result, self.folder / 'analysis', 'completed'
        self.view = self.app.open_laboratory()
        self.view.window.withdraw()
        self.addCleanup(self.clean)

    def clean(self):
        self.root.destroy()
        self.view, self.app, self.root = None, None, None
        gc.collect()

    def wait(self, view=None):
        view = view or self.view
        deadline = time.monotonic() + 8
        while view.busy and time.monotonic() < deadline:
            self.root.update();time.sleep(.01)
        self.assertFalse(view.busy)

    def select(self, test_id):
        index = next(i for i, row in enumerate(self.view.test_table.rows) if row['test_id'] == test_id)
        self.view.test_table.tree.selection_set(str(index))
        self.view.select()
        self.root.update()
        self.assertEqual(self.view.selected_id, test_id)

    def evaluate(self, reason='Preset plan'):
        self.view.reason.set(reason)
        for fields in self.view.repeat_fields:
            fields['value'].set('100')
        self.view.buttons['evaluate'].invoke()
        self.wait()
        self.assertFalse(any(self.view.pending()))

    def export(self):
        with patch('qualitylab_ui.filedialog.askdirectory', return_value=str(self.folder)):
            self.view.buttons['export'].invoke()
            self.wait()
        return json.loads((self.view.output / 'EXPERIMENT.json').read_text(encoding='utf-8'))

    def test_record_switch_retains_drafts_and_hidden_edits_block_export(self):
        view = self.view
        view.run();self.wait()
        view.fields['value'].set('101.25')
        self.select('T2')
        self.assertTrue(view.buttons['export'].instate(['disabled']))
        self.assertTrue(view.buttons['run'].instate(['disabled']))
        self.assertIn('其他', view.status.cget('text'))
        self.app.toggle_language();self.app.toggle_theme()
        self.select('T1')
        self.assertEqual(view.fields['value'].get(), '101.25')
        view.stage()
        self.assertFalse(view.pending()[0])
        view.run();self.wait()
        self.assertEqual(view.result['scenario_metrics']['outside_range_records'], 0)
        self.assertEqual(self.export()['changes']['T1']['value'], 101.25)

    def test_edited_repeat_cannot_export_old_values_and_new_evaluation_retains_history(self):
        view = self.view
        self.evaluate('Original reason')
        first = self.export()
        self.assertTrue(view.confirm_close())
        view.repeat_fields[0]['value'].set('101')
        view.reason.set('Updated reason')
        self.assertTrue(view.buttons['export'].instate(['disabled']))
        self.assertIn('未评价', view.repeat_status.cget('text'))
        with patch('qualitylab_ui.filedialog.askdirectory') as dialog:
            view.export()
            dialog.assert_not_called()
        with patch('qualitylab_ui.messagebox.askyesno', return_value=False) as asked:
            self.assertFalse(view.confirm_close())
            asked.assert_called_once()
        view.buttons['evaluate'].invoke();self.wait()
        second = self.export()
        self.assertEqual(first['rechecks'][0]['attempts'][1]['value'], 100)
        self.assertEqual(second['rechecks'][0]['attempts'][1]['value'], 100)
        self.assertEqual(second['rechecks'][1]['attempts'][1]['value'], 101)
        self.assertEqual(second['rechecks'][1]['reason'], 'Updated reason')
        self.assertEqual(second['rechecks'][1]['attempts'][0]['value'], 90)
        self.assertTrue(view.confirm_close())

    def test_all_repeat_fields_reason_and_round_count_mark_pending(self):
        self.evaluate()
        view = self.view
        variables = [(view.reason, 'Changed reason'), (view.round_count, '2')]
        for fields in view.repeat_fields:
            variables.extend((fields[key], value) for key, value in
                             [('value', '101'), ('spec_low', '96'), ('spec_high', '104'), ('measured_on', '2026-01-03')])
        for variable, value in variables:
            original = variable.get()
            variable.set(value)
            self.assertTrue(view.buttons['export'].instate(['disabled']), (original, value, variable.get(), view.pending()))
            self.assertTrue(view.pending()[1])
            variable.set(original)
            self.assertFalse(any(view.pending()))

    def test_fresh_repeat_draft_requires_close_confirmation_and_survives_selection(self):
        view = self.view
        view.reason.set('New plan')
        view.repeat_fields[0]['value'].set('102')
        with patch('qualitylab_ui.messagebox.askyesno', return_value=False):
            self.assertFalse(view.confirm_close())
        self.select('T2')
        self.assertIn('其他', view.status.cget('text'))
        self.select('T1')
        self.assertEqual(view.reason.get(), 'New plan')
        self.assertEqual(view.repeat_fields[0]['value'].get(), '102')
        view.reset()
        self.assertFalse(any(view.pending()))
        self.assertTrue(view.confirm_close())

    def test_each_record_shows_its_own_repeat_plan_and_evaluated_attempts(self):
        self.evaluate('Plan one')
        self.select('T2')
        self.assertEqual(self.view.repeat_table.rows, [])
        self.assertEqual(self.view.reason.get(), '')
        self.evaluate('Plan two')
        self.select('T1')
        self.assertEqual(self.view.reason.get(), 'Plan one')
        self.assertTrue(all(row['test_id'] == 'T1' for row in self.view.repeat_table.rows))
        exported = self.export()
        self.assertEqual([r['test_id'] for r in exported['rechecks']], ['T1', 'T2'])

    def test_failed_recheck_keeps_old_result_and_changed_form_pending(self):
        self.evaluate()
        previous = self.view.result
        self.view.repeat_fields[0]['measured_on'].set('2025-12-31')
        with patch('qualitylab_ui.messagebox.showerror') as error:
            self.view.evaluate();self.wait()
            error.assert_called_once()
        self.assertIs(self.view.result, previous)
        self.assertEqual(len(self.view.rechecks), 1)
        self.assertTrue(self.view.pending()[1])
        self.assertTrue(self.view.buttons['export'].instate(['disabled']))

    def test_changes_during_worker_do_not_get_labelled_as_evaluated(self):
        view = self.view
        view.reason.set('Captured plan')
        released = threading.Event()
        self.addCleanup(released.set)
        original = view.model.recheck
        def slow(*args):
            released.wait(4)
            return original(*args)
        with patch.object(view.model, 'recheck', side_effect=slow):
            view.evaluate()
            view.reason.set('Later programmatic edit')
            released.set();self.wait()
        self.assertEqual(view.rechecks[-1]['reason'], 'Captured plan')
        self.assertEqual(view.reason.get(), 'Later programmatic edit')
        self.assertTrue(view.pending()[1])

    def test_audit_controls_and_evidence_reachable_at_small_size_in_both_languages(self):
        self.root.deiconify()
        audit = self.app.open_audit()
        audit.generate()
        audit.window.geometry('850x500')
        self.app.adjust_font(3)
        frame = audit.title.master
        def reveal(widget):
            self.root.update()
            y = widget.winfo_rooty() - frame.winfo_rooty()
            height = audit.canvas.bbox('all')[3]
            audit.canvas.yview_moveto(max(0, (y - 8) / height))
            self.root.update()
            top = audit.canvas.winfo_rooty()
            self.assertGreaterEqual(widget.winfo_rooty(), top)
            self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), top + audit.canvas.winfo_height())
        for language in ('zh', 'en'):
            if self.app.language != language:
                self.app.toggle_language()
            for _ in range(4):self.root.update()
            for toolbar, keys in audit.toolbars:
                for key in keys:
                    button = audit.buttons[key]
                    self.assertGreaterEqual(button.winfo_width(), button.winfo_reqwidth())
                    self.assertLessEqual(button.winfo_x() + button.winfo_width(), toolbar.winfo_width())
                    reveal(button)
            reveal(audit.table.tree)
            reveal(audit.scope)


if __name__ == '__main__':
    unittest.main()
