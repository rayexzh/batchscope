"""Independent expected movements, boundary cases and same-snapshot guarantees."""
from collections import Counter
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

from comparison import compare
from quality_ops import analyse
import test_quality_ops as fixtures


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.QualityTests("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.output = self.fixture.root / "comparison"

    def run_comparison(self, start="2026-06-30", end="2026-07-31"):
        return compare(self.fixture.inputs, self.output, start, end)["comparison"]

    def test_counts_ids_and_movements_reconcile_independently(self):
        result = self.run_comparison()
        values = {r["metric"]: (r["before_value"], r["after_value"], r["delta"]) for r in result["metrics"]}
        self.assertEqual(values["measured_records"], (5, 7, 2))
        self.assertEqual(values["open_deviations"], (2, 2, 0))
        self.assertEqual(values["overdue_actions"], (2, 4, 2))
        self.assertEqual({r["test_id"] for r in result["measurements"]}, {"T6", "T7"})
        self.assertEqual({r["deviation_id"]: r["change"] for r in result["deviations"]},
                         {"D1": "closed_since_start", "D3": "opened_still_open", "D4": "still_open"})
        self.assertEqual({r["action_id"]: r["change"] for r in result["actions"]},
                         {"A1": "resolved_overdue", "A2": "newly_overdue", "A3": "newly_overdue",
                          "A5": "still_overdue", "A6": "newly_overdue"})
        actions = {r["action_id"]: r for r in result["actions"]}
        self.assertEqual((actions["A1"]["before_status"], actions["A1"]["after_status"]), ("overdue", "completed"))
        self.assertEqual(actions["A2"]["before_status"], "not_due")  # Due on start date.
        self.assertEqual(actions["A6"]["before_status"], "not_created")
        self.assertEqual(actions["A5"]["after_overdue_days"] - actions["A5"]["before_overdue_days"], 31)
        for name, metric, plus, minus in (("deviations", "open_deviations", "opened_still_open", "closed_since_start"),
                                          ("actions", "overdue_actions", "newly_overdue", "resolved_overdue")):
            counts = Counter(r["change"] for r in result[name])
            old, new, delta = values[metric]
            self.assertEqual(new, old + counts[plus] - counts[minus])
            self.assertEqual(delta, counts[plus] - counts[minus])

    def test_opened_and_closed_between_dates_does_not_increase_backlog(self):
        self.fixture.data["deviations"].append(["D5", "B1", "documentation", "2026-07-02", "2026-07-03"])
        # An overdue episode wholly between endpoints is not an ending overdue movement.
        self.fixture.data["actions"].append(["A7", "D4", "QA", "2026-07-01", "2026-07-02", "2026-07-05"])
        self.fixture.save()
        result = self.run_comparison()
        row = next(r for r in result["deviations"] if r["deviation_id"] == "D5")
        self.assertEqual((row["before_status"], row["after_status"], row["change"]),
                         ("not_opened", "closed", "opened_and_closed"))
        self.assertNotIn("A7", {r["action_id"] for r in result["actions"]})
        self.assertEqual(next(r["delta"] for r in result["metrics"] if r["metric"] == "open_deviations"), 0)

    def test_same_day_and_no_history(self):
        result = self.run_comparison("2026-06-30", "2026-06-30")
        self.assertTrue(all(r["delta"] == 0 for r in result["metrics"]))
        self.assertEqual(result["measurements"], [])
        self.assertEqual({r["change"] for r in result["deviations"]}, {"still_open"})
        self.assertEqual({r["change"] for r in result["actions"]}, {"still_overdue"})
        early = compare(self.fixture.inputs, self.fixture.root / "early", "2025-11-01", "2025-12-31")["comparison"]
        self.assertTrue(all(r["before_value"] == r["after_value"] == 0 for r in early["metrics"]))
        self.assertEqual(early["deviations"], [])
        self.assertEqual(early["actions"], [])

    def test_date_order_and_invalid_dates_create_no_analysis(self):
        for start, end in (("2026-07-31", "2026-06-30"), ("20260630", "2026-07-31"), ("2026-06-30", "2026-02-30")):
            with self.assertRaises(ValueError):
                self.run_comparison(start, end)
            self.assertFalse(self.output.exists())

    def test_future_completion_is_not_leaked_into_end_status(self):
        self.fixture.data["actions"][2][-1] = "2026-08-01"
        self.fixture.save()
        action = next(r for r in self.run_comparison()["actions"] if r["action_id"] == "A3")
        self.assertEqual(action["after_status"], "overdue")
        self.assertEqual(action["completed_on_source"], "2026-08-01")

    def test_source_is_read_once_and_output_hashes_preserve_nested_files(self):
        original = (self.fixture.inputs / "deviations.csv").read_bytes()
        def changed_after_loading(*args):
            after = analyse(*args)
            (self.fixture.inputs / "deviations.csv").write_text("changed after loading", encoding="utf-8")
            return after
        with patch("comparison.analyse", side_effect=changed_after_loading) as call:
            result = self.run_comparison()
        self.assertEqual(call.call_count, 1)
        self.assertEqual(result["input_sha256"]["deviations.csv"], hashlib.sha256(original).hexdigest())
        self.assertEqual(next(r["before_value"] for r in result["metrics"] if r["metric"] == "open_deviations"), 2)
        self.assertIn("end_snapshot/quality.sqlite", result["artifact_sha256"])
        for filename, digest in result["artifact_sha256"].items():
            self.assertEqual(hashlib.sha256((self.output / filename).read_bytes()).hexdigest(), digest)
        with self.assertRaises(ValueError):
            self.run_comparison()

    def test_bad_input_blocks_parent_completion_manifest(self):
        self.fixture.data["actions"][0][1] = "orphan"
        self.fixture.save()
        with self.assertRaises(ValueError):
            self.run_comparison()
        self.assertTrue((self.output / "end_snapshot/INPUT_ISSUES.csv").is_file())
        self.assertFalse((self.output / "manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
