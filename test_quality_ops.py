import csv
import gc
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch

from quality_ops import COLUMNS, analyse, generate, write_csv
from review import filter_details, group_details


def cleanup_gui(root):
    root.destroy()
    # Tk objects from completed test windows must be collected on the UI thread.
    gc.collect()


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        self.data = {
            "batches": [["B1", "Demo-A", "2026-01-01"], ["B2", "Demo-Future", "2026-07-01"]],
            "test_results": [
                ["T1", "B1", "assay", "demo-HPLC", 100, "%", 95, 105, "%", "2026-01-02"],
                ["T2", "B1", "assay", "demo-HPLC", None, "%", 95, 105, "%", "2026-01-02"],
                ["T3", "B1", "assay", "demo-HPLC", 106, "%", 95, 105, "%", "2026-01-02"],
                ["T4", "B1", "assay", "demo-HPLC", 95, "%", 95, 105, "%", "2026-01-02"],
                ["T5", "B1", "assay", "demo-HPLC", 105, "%", 95, 105, "%", "2026-01-02"],
                ["T6", "B1", "assay", "demo-HPLC", 100, "%", 95, 105, "%", "2026-07-01"],
                ["T7", "B2", "assay", "demo-HPLC", 100, "%", 95, 105, "%", "2026-07-02"],
            ],
            "deviations": [
                ["D1", "B1", "laboratory", "2026-06-01", "2026-07-15"],
                ["D2", "B1", "laboratory", "2026-06-10", "2026-06-20"],
                ["D3", "B1", "documentation", "2026-07-01", None],
                ["D4", "B1", "documentation", "2026-06-20", None],
            ],
            "actions": [
                ["A1", "D1", "QC", "2026-06-02", "2026-06-29", "2026-07-01"],
                ["A2", "D1", "QA", "2026-06-02", "2026-06-30", None],
                ["A3", "D1", "QC", "2026-06-02", "2026-07-01", None],
                ["A4", "D2", "QA", "2026-06-11", "2026-06-12", "2026-06-15"],
                ["A5", "D4", "QA", "2026-06-21", "2026-06-29", None],
                ["A6", "D3", "QC", "2026-07-02", "2026-07-05", None],
            ],
        }
        self.save()

    def save(self):
        for table, rows in self.data.items():
            write_csv(self.inputs / f"{table}.csv", COLUMNS[table], rows)
        (self.inputs / "SOURCE.json").write_text('{"data_type":"synthetic","fixture":true}', encoding="utf-8")

    def run_case(self, as_of="2026-06-30", output="results"):
        return analyse(self.inputs, self.root / output, as_of)

    def test_range_denominator_and_inclusive_boundaries(self):
        report = self.run_case()
        self.assertEqual(report["metrics"], {"measured_records": 5, "judgeable_records": 4,
            "missing_records": 1, "outside_range_records": 1, "open_deviations": 2, "overdue_actions": 2})
        rows = report["reports"]["01_test_ranges"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["outside_range_pct"], 25)
        with closing(sqlite3.connect(self.root / "results/quality.sqlite")) as db:
            self.assertIsNone(db.execute("SELECT value FROM test_results WHERE test_id='T2'").fetchone()[0])
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_as_of_excludes_future_information(self):
        report = self.run_case()
        lab = next(r for r in report["reports"]["02_deviation_backlog"] if r["category"] == "laboratory")
        self.assertEqual((lab["open_records"], lab["oldest_open_days"], lab["closed_records"], lab["mean_closed_duration_days"]), (1, 29, 1, 10))
        overdue = report["reports"]["03_overdue_actions"]
        self.assertEqual([r["action_id"] for r in overdue], ["A1", "A5"])
        later = self.run_case("2026-07-31", "later")
        self.assertEqual(later["metrics"]["measured_records"], 7)
        self.assertEqual(later["metrics"]["overdue_actions"], 4)
        self.assertEqual([r["action_id"] for r in later["reports"]["03_overdue_actions"]], ["A5", "A2", "A3", "A6"])

    def test_all_missing_and_empty_history_are_not_zero_rates(self):
        for row in self.data["test_results"]:
            row[4] = None
        self.save()
        self.assertIsNone(self.run_case()["reports"]["01_test_ranges"][0]["outside_range_pct"])
        early = self.run_case("2025-12-31", "early")
        self.assertEqual(early["metrics"]["measured_records"], 0)
        self.assertEqual(early["metrics"]["open_deviations"], 0)
        self.assertEqual(early["reports"]["01_test_ranges"], [])

    def assert_blocked(self):
        self.save()
        with self.assertRaises(ValueError):
            self.run_case()
        self.assertTrue((self.root / "results/INPUT_ISSUES.csv").is_file())
        self.assertFalse((self.root / "results/manifest.json").exists())
        self.assertFalse((self.root / "results/quality.sqlite").exists())

    def test_orphans_block_analysis(self):
        self.data["actions"][0][1] = "unknown"
        self.assert_blocked()

    def test_duplicate_keys_block_analysis(self):
        self.data["test_results"].append(self.data["test_results"][0].copy())
        self.assert_blocked()

    def test_unit_mismatch_blocks_analysis(self):
        self.data["test_results"][0][5] = "mg"
        self.assert_blocked()

    def test_invalid_order_of_dates_and_bounds(self):
        self.data["deviations"][0][-1] = "2026-05-31"
        self.data["actions"][1][4] = "2026-01-01"
        self.data["test_results"][0][6] = 120
        self.assert_blocked()

    def test_nonfinite_numbers_and_invalid_iso_dates(self):
        self.data["test_results"][0][4] = "NaN"
        self.data["batches"][0][2] = "2026-02-30"
        self.assert_blocked()
        with self.assertRaises(ValueError):
            self.run_case("20260630", "bad-date")

    def test_provenance_and_preservation(self):
        (self.inputs / "SOURCE.json").write_text('{"data_type":"real"}', encoding="utf-8")
        with self.assertRaises(ValueError):
            self.run_case()
        self.save()
        report = self.run_case()
        with self.assertRaises(ValueError):
            self.run_case()
        for filename, digest in report["artifact_sha256"].items():
            self.assertEqual(hashlib.sha256((self.root / "results" / filename).read_bytes()).hexdigest(), digest)

    def test_generator_is_reproducible(self):
        for name in ("one", "two"):
            self.assertEqual(generate(self.root / name), {"batches": 100, "test_results": 200, "deviations": 33, "actions": 66})
        for f in (self.root / "one").iterdir():
            self.assertEqual(f.read_bytes(), (self.root / "two" / f.name).read_bytes())
        # Two of the 200 generated measurements occur in July and are out of scope.
        self.assertEqual(analyse(self.root / "one", self.root / "generated-analysis", "2026-06-30")["metrics"]["measured_records"], 198)

    def test_csv_formula_text_is_escaped(self):
        path = self.root / "export.csv"
        write_csv(path, ["text", "number"], [["=1+1", -3]])
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
        self.assertEqual(rows[1], ["'=1+1", "-3"])

    def test_details_reconcile_with_each_summary_at_two_dates(self):
        for day, folder in (("2026-06-30", "june"), ("2026-07-31", "july")):
            result = self.run_case(day, folder)
            for group in result["reports"]["01_test_ranges"]:
                rows = group_details(result, "01_test_ranges", group)
                self.assertEqual(len(rows), group["measured_records"])
                self.assertEqual(len(filter_details(rows, "missing")), group["missing_records"])
                self.assertEqual(len(filter_details(rows, "outside_range")), group["outside_range_records"])
                self.assertEqual(sum(r["value"] is not None for r in rows), group["judgeable_records"])
            for group in result["reports"]["02_deviation_backlog"]:
                rows = group_details(result, "02_deviation_backlog", group)
                self.assertEqual(len(rows), group["opened_to_date"])
                self.assertEqual(len(filter_details(rows, "open")), group["open_records"])
                self.assertEqual(len(filter_details(rows, "closed")), group["closed_records"])
            self.assertEqual(len(result["details"]["03_overdue_actions"]), result["metrics"]["overdue_actions"])
            for action in result["reports"]["03_overdue_actions"]:
                rows = group_details(result, "03_overdue_actions", action)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["overdue_days"], action["overdue_days"])
                self.assertEqual(rows[0]["batch_id"], "B1")
            for name in ("01_test_ranges", "02_deviation_backlog", "03_overdue_actions"):
                self.assertIn(name + "_details.csv", result["artifact_sha256"])

    def test_details_keep_product_method_unit_and_bounds_separate(self):
        variants = [("T8", "B1", "demo-HPLC", "%", 0, 200),
                    ("T9", "B1", "other-method", "%", 95, 105),
                    ("T10", "B1", "demo-HPLC", "mg", 95, 105),
                    ("T11", "B3", "demo-HPLC", "%", 95, 105)]
        self.data["batches"].append(["B3", "Demo-Other", "2026-01-01"])
        for test, batch, method, unit, low, high in variants:
            self.data["test_results"].append([test, batch, "assay", method, 106, unit, low, high, unit, "2026-01-02"])
        self.save()
        result = self.run_case()
        self.assertEqual(len(result["reports"]["01_test_ranges"]), 5)
        for group in result["reports"]["01_test_ranges"]:
            rows = group_details(result, "01_test_ranges", group)
            self.assertEqual(len(rows), group["measured_records"])
        wide = next(g for g in result["reports"]["01_test_ranges"] if g["spec_high"] == 200)
        self.assertEqual([r["test_id"] for r in group_details(result, "01_test_ranges", wide)], ["T8"])
        self.assertEqual(wide["outside_range_records"], 0)

    def test_detail_statuses_use_snapshot_not_future_completion(self):
        result = self.run_case()
        deviations = {r["deviation_id"]: r for r in result["details"]["02_deviation_backlog"]}
        self.assertNotIn("D3", deviations)
        self.assertEqual(deviations["D1"]["snapshot_status"], "open")
        self.assertEqual(deviations["D1"]["open_age_days"], 29)
        self.assertEqual(deviations["D1"]["closed_on_source"], "2026-07-15")
        self.assertIsNone(deviations["D1"]["closed_duration_days"])
        self.assertEqual(deviations["D2"]["closed_duration_days"], 10)
        actions = {r["action_id"]: r for r in result["details"]["03_overdue_actions"]}
        self.assertEqual(set(actions), {"A1", "A5"})
        self.assertEqual(actions["A1"]["completed_on_source"], "2026-07-01")
        self.assertEqual(actions["A1"]["snapshot_status"], "overdue")

    def test_detail_filters_handle_missing_results_and_chinese_search(self):
        rows = self.run_case()["details"]["01_test_ranges"]
        self.assertEqual([r["test_id"] for r in filter_details(rows, "missing")], ["T2"])
        self.assertIsNone(filter_details(rows, "missing")[0]["value"])
        self.assertEqual([r["test_id"] for r in filter_details(rows, search="超出示例范围")], ["T3"])
        self.assertEqual([r["test_id"] for r in filter_details(rows, "within_range", " t4 ")], ["T4"])
        self.assertEqual(filter_details(rows, "missing", "T3"), [])
        self.assertEqual(len(filter_details(rows, search="b1")), 5)

    def test_desktop_detail_view_uses_completed_snapshot(self):
        from app import Window
        with patch("app.ROOT", self.root):
            root = tk.Tk()
            root.withdraw()
            self.addCleanup(cleanup_gui, root)
            app = Window(root)
            app.inputs.set(str(self.inputs))
            app.start()
            deadline = time.monotonic() + 10
            while app.busy and time.monotonic() < deadline:
                root.update()
                time.sleep(.01)
            self.assertFalse(app.busy)
            self.assertEqual(str(app.detail_button["state"]), "normal")
            tree = app.tables["01_test_ranges"]
            self.assertIn("检验记录数", tree.heading("measured_records", "text"))
            tree.selection_set("0")
            # Editing the date/input after running must not change the existing result.
            app.as_of.set("2026-07-31")
            self.data["test_results"][2][4] = 100
            self.save()
            detail = app.open_selected_details()
            detail.window.withdraw()
            self.assertEqual(detail.as_of, "2026-06-30")
            self.assertEqual(len(detail.rows), 5)
            detail.status_filter.current(1)
            detail.refresh()
            self.assertEqual([r["test_id"] for r in detail.visible_rows], ["T3"])
            self.assertEqual(detail.visible_rows[0]["value"], 106)
            detail.search.set("no-such-record")
            self.assertEqual(detail.visible_rows, [])
            self.assertIn("0 / 5", detail.counts.get())
            # Header/blank-space double clicks must not open a stale selection.
            from types import SimpleNamespace
            with patch.object(tree, "identify_row", return_value=""):
                self.assertIsNone(app.open_details("01_test_ranges", SimpleNamespace(y=0)))

    def test_desktop_recovers_after_failed_analysis(self):
        from app import Window
        root_patch = patch("app.ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        root = tk.Tk()
        root.withdraw()
        self.addCleanup(cleanup_gui, root)
        app = Window(root)
        app.inputs.set(str(self.inputs))
        def run():
            app.start()
            self.assertTrue(app.busy)
            deadline = time.monotonic() + 10
            while app.busy and time.monotonic() < deadline:
                root.update()
                time.sleep(.01)
            self.assertFalse(app.busy)
        app.as_of.set("invalid")
        run()
        self.assertIn(app.t("failed"), app.status.get())
        self.assertIsNone(app.result)
        self.assertEqual(str(app.detail_button["state"]), "disabled")
        self.assertFalse(app.tables["01_test_ranges"].get_children())
        app.as_of.set("2026-06-30")
        run()
        self.assertIn(app.t("completed"), app.status.get())
        self.assertEqual(len(app.tables["03_overdue_actions"].get_children()), 2)
        self.assertTrue((app.output / "manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
