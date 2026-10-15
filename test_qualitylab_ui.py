"""Exercise the laboratory through the same controls used in the desktop app."""
from copy import deepcopy
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
from comparison import compare
from test_qualitylab import fixture


class LaboratoryUiTests(unittest.TestCase):
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

    def wait(self, condition):
        until = time.monotonic() + 8
        while not condition() and time.monotonic() < until:
            self.root.update()
            time.sleep(.005)
        self.assertTrue(condition())

    def run_comparison(self):
        self.view.buttons['run'].invoke()
        self.wait(lambda: not self.view.busy)

    def test_edit_run_stale_export_guard_and_restore(self):
        view = self.view
        before = deepcopy(self.app.result)
        view.fields['value'].set('100')
        view.buttons['stage'].invoke()
        self.assertEqual(view.model.changes['T1']['value'], 100)
        self.run_comparison()
        self.assertEqual(view.result['scenario_metrics']['outside_range_records'], 0)
        self.assertTrue(view.buttons['export'].instate(['!disabled']))
        view.as_of.set('2026-07-31')
        self.assertTrue(view.buttons['export'].instate(['disabled']))
        self.assertIn('重新运行', view.status.cget('text'))
        view.buttons['restore'].invoke()
        self.assertEqual(view.model.changes, {})
        self.assertEqual(view.fields['value'].get(), '90.0')
        self.assertEqual(self.app.result, before)

    def test_presentation_changes_preserve_unsaved_form_and_repeat_plan(self):
        view = self.view
        view.fields['value'].set('101.25')
        view.repeat_fields[0]['value'].set('100.1')
        view.reason.set('Preset training explanation')
        self.app.toggle_language()
        self.app.toggle_theme()
        self.app.adjust_font(2)
        self.root.update()
        self.assertEqual(view.fields['value'].get(), '101.25')
        self.assertEqual(view.repeat_fields[0]['value'].get(), '100.1')
        self.assertEqual(view.reason.get(), 'Preset training explanation')
        self.assertEqual(view.title.cget('text'), 'Quality data laboratory')
        self.assertEqual(view.selected_id, 'T1')

    def test_repeat_practice_keeps_initial_outside_result_and_export(self):
        view = self.view
        view.reason.set('Exercise: all results remain visible')
        for fields in view.repeat_fields:
            fields['value'].set('100')
        view.buttons['evaluate'].invoke()
        self.wait(lambda: not view.busy)
        self.assertEqual(len(view.repeat_table.rows), 3)
        self.assertEqual(view.repeat_table.rows[0]['value'], 90)
        self.assertTrue(view.rechecks[0]['any_outside_range'])
        with patch('qualitylab_ui.filedialog.askdirectory', return_value=str(self.folder)):
            view.buttons['export'].invoke()
        self.wait(lambda: not view.busy)
        exported = json.loads((view.output / 'EXPERIMENT.json').read_text(encoding='utf-8'))
        self.assertTrue(exported['rechecks'][0]['any_outside_range'])
        self.assertTrue((view.output / 'manifest.json').exists())
        self.assertTrue(view.confirm_close())
        self.app.toggle_language()
        with patch('qualitylab_ui.os.startfile', create=True) as opened:
            view.buttons['open'].invoke()
            self.assertEqual(opened.call_args.args[0].name, 'LAB.en.html')

    def test_failed_input_retains_previous_success_and_worker_keeps_ui_live(self):
        view = self.view
        self.run_comparison()
        previous = view.result
        view.as_of.set('2026-02-30')
        with patch('qualitylab_ui.messagebox.showerror') as error:
            view.buttons['run'].invoke()
            self.wait(lambda: not view.busy)
            error.assert_called_once()
        self.assertIs(view.result, previous)
        self.assertTrue(view.buttons['export'].instate(['disabled']))
        view.as_of.set('2026-06-30')
        released = threading.Event()
        self.addCleanup(released.set)
        def slow(_):
            released.wait(3)
            return previous
        with patch.object(view.model, 'run', side_effect=slow):
            view.buttons['run'].invoke()
            heartbeats = []
            self.root.after(10, lambda: heartbeats.append(True))
            self.wait(lambda: bool(heartbeats))
            self.assertTrue(view.busy)
            self.app.toggle_language()
            self.assertTrue(view.buttons['run'].instate(['disabled']))
            released.set()
            self.wait(lambda: not view.busy)

    def test_snapshot_ignores_later_main_window_changes_and_detects_bad_hash(self):
        original = self.view.model.source_sha256
        self.app.result, self.app.output = None, None
        self.run_comparison()
        self.assertEqual(self.view.result['source_sha256'], original)
        self.app.result, self.app.output = self.result, self.folder / 'analysis'
        self.result['artifact_sha256']['quality.sqlite'] = 'wrong'
        with patch('app.messagebox.showerror') as error:
            self.assertIsNone(self.app.open_laboratory())
            error.assert_called_once()

    def test_open_lab_from_two_date_comparison_uses_end_snapshot(self):
        result = compare(self.inputs, self.folder / 'comparison', '2026-01-01', '2026-06-30')
        self.app.result, self.app.output = result, self.folder / 'comparison'
        other = self.app.open_laboratory()
        other.window.withdraw()
        self.assertIsNotNone(other)
        self.assertIn('end_snapshot', other.model.source)
        self.assertEqual(other.model.run('2026-06-30')['baseline_metrics'], result['metrics'])

    def test_reset_and_close_do_not_silently_discard_unexported_edits(self):
        view = self.view
        view.fields['value'].set('100')
        view.stage()
        with patch('qualitylab_ui.messagebox.askyesno', return_value=False):
            self.assertFalse(view.confirm_close())
        view.reset()
        self.assertEqual(view.model.changes, {})
        self.assertIsNone(view.result)
        self.assertTrue(view.confirm_close())

    def test_unstaged_form_edits_cannot_export_or_silently_run_old_settings(self):
        view = self.view
        self.run_comparison()
        original = view.result
        view.fields['value'].set('100')
        self.assertTrue(view.buttons['run'].instate(['disabled']))
        self.assertTrue(view.buttons['export'].instate(['disabled']))
        view.run()
        self.assertIs(view.result, original)
        self.assertFalse(view.busy)
        view.stage()
        self.assertTrue(view.buttons['run'].instate(['!disabled']))
        self.run_comparison()
        self.assertEqual(view.result['scenario_metrics']['outside_range_records'], 0)

    def test_small_window_and_large_font_keep_actions_and_attempts_reachable(self):
        self.root.deiconify()
        view = self.view
        view.window.deiconify()
        view.window.geometry('850x600')
        self.app.toggle_language()
        self.app.adjust_font(3)
        self.root.update()
        for key in ('run', 'export', 'open'):
            button = view.buttons[key]
            self.assertLessEqual(button.winfo_x() + button.winfo_width(), view.action_row.winfo_width())
            self.assertGreaterEqual(button.winfo_width(), button.winfo_reqwidth())
        view.book.select(2)
        for _ in range(4): self.root.update()
        view.canvas.yview_moveto(1)
        self.root.update()
        self.assertLessEqual(view.repeat_table.tree.winfo_rooty() + view.repeat_table.tree.winfo_height(),
                             view.canvas.winfo_rooty() + view.canvas.winfo_height())


if __name__ == '__main__':
    unittest.main()
