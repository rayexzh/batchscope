"""Run preflight through the native controls, including failure and small-window flows."""
import gc
import csv
import json
from pathlib import Path
import tempfile
import threading
import time
import tkinter as tk
import unittest
from unittest.mock import patch

from app import Window
from quality_ops import check_inputs
from test_qualitylab import fixture


class InputCheckUiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.inputs, self.baseline = fixture(self.folder)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = Window(self.root)
        self.app.inputs.set(str(self.inputs))
        self.view = self.app.open_inputcheck()
        self.view.window.withdraw()
        self.addCleanup(self.clean)

    def clean(self):
        self.root.destroy()
        self.view, self.app, self.root = None, None, None
        gc.collect()

    def wait(self, condition):
        deadline = time.monotonic() + 8
        while not condition() and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.01)
        self.assertTrue(condition(), 'Desktop operation did not complete.')

    def run_check(self):
        self.view.buttons['check'].invoke()
        self.wait(lambda: not self.view.busy)

    def test_check_before_analysis_and_folder_change_preserves_previous_snapshot(self):
        self.assertIsNone(self.app.result)
        self.assertEqual(self.view.folder.get(), str(self.inputs))
        self.run_check()
        self.assertIsNone(self.app.result)
        self.assertTrue(self.view.result['can_analyse'])
        self.assertEqual(len(self.view.profile_table.rows), 4)
        previous = self.view.result
        self.view.folder.set(str(self.folder / 'another-folder'))
        self.assertTrue(self.view.stale())
        self.assertTrue(self.view.buttons['export'].instate(['disabled']))
        self.assertIs(self.view.result, previous)
        self.view.folder.set(str(self.inputs))
        self.assertFalse(self.view.stale())
        self.assertTrue(self.view.buttons['export'].instate(['!disabled']))

    def test_language_theme_and_search_preserve_result_and_export_all_rows(self):
        self.run_check()
        previous = self.view.result
        self.view.search.set('提示')
        self.assertEqual(len(self.view.finding_table.rows), 1)
        self.view.search.set('nothing matches')
        self.assertEqual(self.view.finding_table.rows, [])
        self.app.toggle_language()
        self.app.toggle_theme()
        self.root.update()
        self.assertEqual(self.view.title.cget('text'), 'Check input data')
        self.assertIs(self.view.result, previous)
        self.view.search.set('Note')
        self.assertEqual(len(self.view.finding_table.rows), 1)
        self.view.search.set('nothing matches')
        with patch('input_check_ui.filedialog.askdirectory', return_value=str(self.folder)):
            self.view.buttons['export'].invoke()
            self.wait(lambda: not self.view.busy)
        exported = list(self.folder.glob('BatchScope-input-check-*/report/INPUT_CHECK.json'))
        self.assertEqual(len(exported), 1)
        saved = json.loads(exported[0].read_text(encoding='utf-8'))
        self.assertEqual(saved['findings'], previous['findings'])
        self.assertTrue((exported[0].parent / 'manifest.json').exists())

    def test_failed_job_keeps_previous_result_and_worker_leaves_gui_responsive(self):
        self.run_check()
        previous = self.view.result
        with patch('input_check_ui.check_inputs', side_effect=ValueError('Demo check failure')):
            with patch('input_check_ui.messagebox.showerror') as error:
                self.run_check()
                error.assert_called_once()
        self.assertIs(self.view.result, previous)
        released = threading.Event()
        self.addCleanup(released.set)
        def slow(folder):
            released.wait(5)
            return check_inputs(folder)
        with patch('input_check_ui.check_inputs', side_effect=slow) as worker:
            self.view.check()
            heartbeats = []
            self.root.after(10, lambda: heartbeats.append(True))
            self.wait(lambda: bool(heartbeats))
            self.assertTrue(self.view.busy)
            self.view.check()
            self.app.toggle_language()
            self.assertTrue(self.view.buttons['check'].instate(['disabled']))
            with patch('input_check_ui.messagebox.showinfo'):
                self.assertFalse(self.view.confirm_close())
            released.set()
            self.wait(lambda: not self.view.busy)
            self.assertEqual(worker.call_count, 1)

    def test_narrow_window_larger_font_keeps_controls_and_notes_visible(self):
        self.run_check()
        self.app.adjust_font(3)
        self.root.deiconify()
        self.view.window.deiconify()
        self.view.window.geometry('850x600')
        for _ in range(5):
            self.root.update()
        for lang in ('zh', 'en'):
            if self.app.language != lang:
                self.app.toggle_language()
            self.root.update()
            right = self.view.window.winfo_rootx() + self.view.window.winfo_width()
            bottom = self.view.window.winfo_rooty() + self.view.window.winfo_height()
            for widget in [*self.view.buttons.values(), self.view.note]:
                self.assertTrue(widget.winfo_ismapped())
                self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(), right)
                self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), bottom)
            self.assertGreater(self.view.finding_table.tree.winfo_height(), 45)

    def test_long_finding_can_be_opened_without_horizontal_scrolling(self):
        self.run_check()
        self.view.finding_table.tree.selection_set('0')
        detail = self.view.finding_table.open_row()
        self.assertIsNotNone(detail)
        # ScrolledText wraps its Text widget in a frame with a scrollbar.
        content = ''.join(widget.get('1.0', 'end') for widget in detail.winfo_children()[0].winfo_children()
                          if isinstance(widget, tk.Text))
        self.assertIn('检验结果为空', content)
        detail.destroy()

    def test_mixed_ranges_show_both_values_and_translate_the_warning(self):
        path = self.inputs / 'test_results.csv'
        with path.open(encoding='utf-8-sig', newline='') as handle:
            rows = list(csv.reader(handle))
        rows[2][6] = '85'
        with path.open('w', encoding='utf-8-sig', newline='') as handle:
            csv.writer(handle).writerows(rows)
        self.run_check()
        self.view.search.set('规格')
        self.assertEqual(len(self.view.finding_table.rows), 3)
        self.view.finding_table.tree.selection_set('0')
        detail = self.view.finding_table.open_row()
        content = ''.join(widget.get('1.0', 'end') for widget in detail.winfo_children()[0].winfo_children()
                          if isinstance(widget, tk.Text))
        self.assertIn('非批准值', content)
        self.assertIn('85 .. 105', content)
        detail.destroy()
        self.app.toggle_language()
        self.view.search.set('specification')
        self.assertEqual(len(self.view.finding_table.rows), 3)


if __name__ == '__main__':
    unittest.main()
