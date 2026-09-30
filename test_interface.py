"""Interaction regressions that protect record identity and calculations."""
from pathlib import Path
import tempfile
import gc
import threading
import time
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app import Window
from quality_ops import analyse, generate
from comparison import compare
from review import clipboard_row


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        generate(self.folder / "inputs", batches=20)
        self.result = analyse(self.folder / "inputs", self.folder / "results", "2026-06-30")
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.cleanup_gui)
        self.app = Window(self.root)
        self.app.result, self.app.output, self.app.phase = self.result, self.folder / "results", "completed"
        self.app.apply_view()

    def cleanup_gui(self):
        self.root.destroy()
        self.app = None
        self.root = None
        gc.collect()

    def test_language_and_theme_preserve_data_filter_and_selection(self):
        app = self.app
        table = app.record_tables["01_test_ranges"]
        table.tree.selection_set("0")
        detail = app.open_details("01_test_ranges")
        detail.window.withdraw()
        detail.status_filter.current(1)
        detail.refresh()
        before = list(detail.visible_rows)
        metrics = app.result["metrics"].copy()
        app.toggle_language()
        self.assertEqual(app.title["text"], "BatchScope")
        self.assertEqual(table.tree.heading("outside_range_records", "text"), "Outside")
        self.assertEqual(detail.status_filter.get(), "Outside range")
        self.assertEqual(detail.visible_rows, before)
        self.assertEqual(table.tree.selection(), ("0",))
        app.toggle_theme()
        self.assertEqual(app.theme, "dark")
        self.assertEqual(ttk.Style(self.root).lookup("Treeview", "fieldbackground"), app.colors["surface"])
        self.assertEqual(detail.window["background"], app.colors["background"])
        app.toggle_language()
        self.assertEqual(table.tree.heading("outside_range_records", "text"), "超范围数")
        self.assertEqual(app.result["metrics"], metrics)

    def test_numeric_sort_keeps_missing_last_and_row_identity(self):
        table = self.app.record_tables["01_test_ranges"]
        rows = [{"test_id": "T-small", "value": 2}, {"test_id": "T-big", "value": 100},
                {"test_id": "T-missing", "value": None}, {"test_id": "T-ten", "value": 10}]
        table.populate(rows)
        table.sort("value")
        self.assertEqual(table.tree.get_children(), ("0", "3", "1", "2"))
        table.tree.selection_set("3")
        self.assertEqual(table.selected()["test_id"], "T-ten")
        table.sort("value")
        self.assertEqual(table.tree.get_children(), ("1", "3", "0", "2"))
        table.populate(rows, preserve=True)
        self.assertEqual(table.tree.get_children(), ("1", "3", "0", "2"))
        self.assertEqual(table.selected()["test_id"], "T-ten")

    def test_right_click_targets_clicked_row_and_ignores_empty_space(self):
        table = self.app.record_tables["03_overdue_actions"]
        self.assertGreater(len(table.rows), 1)
        table.tree.selection_set("0")
        event = SimpleNamespace(y=70, x_root=100, y_root=100)
        with patch.object(table.tree, "identify_row", return_value="1"), \
             patch.object(table.menu, "tk_popup") as popup, patch.object(table.menu, "grab_release"):
            table.popup(event)
            popup.assert_called_once_with(100, 100)
        self.assertEqual(table.selected(), table.rows[1])
        with patch.object(table.tree, "identify_row", return_value=""), patch.object(table.menu, "tk_popup") as popup:
            table.popup(event)
            popup.assert_not_called()
        detail = table.open_row()
        detail.window.withdraw()
        self.assertEqual(detail.rows[0]["action_id"], table.rows[1]["action_id"])

    def test_copy_uses_actual_selection_and_current_language(self):
        app = self.app
        app.toggle_language()
        table = app.record_tables["03_overdue_actions"]
        table.tree.selection_set("0")
        action = table.selected()["action_id"]
        table.copy_row()
        copied = self.root.clipboard_get()
        self.assertIn("Action", copied.splitlines()[0])
        self.assertIn(action, copied.splitlines()[1])
        table.copy_id()
        self.assertEqual(self.root.clipboard_get(), action)

    def test_font_controls_and_closed_details_do_not_break_refresh(self):
        app = self.app
        app.record_tables["01_test_ranges"].tree.selection_set("0")
        detail = app.open_details("01_test_ranges")
        detail.window.destroy()
        app.adjust_font(1)
        self.assertEqual(app.font_size, 12)
        self.assertEqual(app.details, [])
        for _ in range(8):
            app.adjust_font(1)
        self.assertEqual(app.font_size, 14)
        for _ in range(8):
            app.adjust_font(-1)
        self.assertEqual(app.font_size, 10)
        self.assertEqual(app.metric_cards["overdue_actions"][0]["text"], str(app.result["metrics"]["overdue_actions"]))

    def test_clipboard_export_escapes_formula_text_without_changing_numbers(self):
        import csv
        import io
        copied = clipboard_row(["product", "value"], {"product": "=1+1\tmore", "value": -3}, "en")
        rows = list(csv.reader(io.StringIO(copied), delimiter="\t"))
        self.assertEqual(rows[1], ["'=1+1\tmore", "-3"])

    def test_switching_view_during_analysis_preserves_busy_state(self):
        app = self.app
        app.inputs.set(str(self.folder / "inputs"))
        gate = threading.Event()
        original = app.worker
        def worker(*args):
            gate.wait(5)
            original(*args)
        with patch("app.ROOT", self.folder), patch.object(app, "worker", side_effect=worker):
            try:
                app.start()
                app.toggle_language()
                app.toggle_theme()
                self.assertTrue(app.busy)
                self.assertEqual(str(app.run_button["state"]), "disabled")
                self.assertEqual(str(app.input_entry["state"]), "disabled")
                self.assertIn("Validating", app.status.get())
            finally:
                gate.set()
            deadline = time.monotonic() + 10
            while app.busy and time.monotonic() < deadline:
                self.root.update()
                time.sleep(.01)
            self.assertFalse(app.busy)
            self.assertIn("Completed", app.status.get())
            self.assertEqual(app.progress.winfo_manager(), "")
            self.assertEqual(app.result["metrics"], self.result["metrics"])

    def test_comparison_window_filters_language_and_fixed_dates(self):
        app = self.app
        app.result = compare(self.folder / "inputs", self.folder / "comparison", "2026-06-30", "2026-07-31")
        view = app.open_comparison()
        view.window.withdraw()
        view.book.select(2)
        view.refresh()
        self.assertNotIn("still_overdue", {r["change"] for r in view.visible_rows["actions"]})
        view.changed.set(False)
        view.search.set("持续逾期")
        self.assertGreater(len(view.visible_rows["actions"]), 0)
        self.assertEqual({r["change"] for r in view.visible_rows["actions"]}, {"still_overdue"})
        rows = list(view.visible_rows["actions"])
        view.tables["actions"].tree.selection_set("0")
        app.as_of.set("2030-01-01")
        app.from_date.set("2020-01-01")
        app.toggle_language()
        app.toggle_theme()
        self.assertEqual(view.visible_rows["actions"], rows)
        self.assertEqual(view.tables["actions"].selected(), rows[0])
        self.assertIn("2026-06-30", view.dates["text"])
        self.assertIn("2026-07-31", view.dates["text"])
        self.assertNotIn("2030", view.dates["text"])
        view.window.destroy()
        app.apply_view()
        self.assertEqual(app.comparisons, [])

    def test_background_comparison_failure_and_recovery(self):
        app = self.app
        app.inputs.set(str(self.folder / "inputs"))
        app.from_date.set("2026-07-31")
        def wait():
            deadline = time.monotonic() + 10
            while app.busy and time.monotonic() < deadline:
                self.root.update()
                time.sleep(.01)
            self.assertFalse(app.busy)
        with patch("app.ROOT", self.folder):
            app.start(comparison=True)
            self.assertEqual(str(app.compare_button["state"]), "disabled")
            self.assertEqual(str(app.from_entry["state"]), "disabled")
            wait()
            self.assertEqual(app.phase, "failed")
            self.assertIsNone(app.result)
            self.assertEqual(str(app.view_compare_button["state"]), "disabled")
            app.from_date.set("2026-06-30")
            app.as_of.set("2026-07-31")
            app.start(comparison=True)
            app.toggle_language()
            wait()
            self.assertEqual(app.phase, "completed")
            self.assertEqual(app.result["as_of"], "2026-07-31")
            self.assertEqual(str(app.view_compare_button["state"]), "normal")
            self.assertEqual(len(app.comparisons), 1)
            self.assertTrue((app.output / "COMPARISON.md").is_file())

    def test_workbench_filters_and_batch_trace_survive_presentation_changes(self):
        app = self.app
        view = app.open_workbench()
        view.window.withdraw()
        view.filter.current(1)
        view.refresh()
        self.assertEqual(len(view.visible_rows["queue"]), app.result["operations"]["metrics"]["outstanding_actions"])
        view.tables["queue"].sort("days_until_due", True)
        view.tables["queue"].tree.selection_set("0")
        selected = view.tables["queue"].selected()
        batch = view.open_batch()
        batch.window.withdraw()
        self.assertEqual(batch.result["batch"]["batch_id"], selected["batch_id"])
        self.assertGreater(len(batch.result["measurements"]),0)
        app.as_of.set("2030-01-01")
        app.toggle_language()
        app.toggle_theme()
        self.assertEqual(batch.result["as_of"],"2026-06-30")
        self.assertEqual(view.filter.current(),1)
        self.assertEqual(view.tables["queue"].selected(),selected)
        chosen = next(r["batch_id"] for r in app.result["operations"]["batches"] if r["batch_id"] != selected["batch_id"])
        view.batch.set(chosen)
        view.choose_batch()
        another = view.open_batch()
        another.window.withdraw()
        self.assertEqual(another.result["batch"]["batch_id"], chosen)
        another.window.destroy()
        view.search.set("no-such-action")
        self.assertEqual(view.visible_rows["queue"],[])
        view.window.destroy()
        batch.window.destroy()
        app.apply_view()
        self.assertEqual(app.review_views,[])


if __name__ == "__main__":
    unittest.main()
