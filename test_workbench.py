"""Expected operational states, transparent date rules and portable output paths."""
from datetime import date, timedelta
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import runtime_paths
import test_quality_ops as fixtures
from quality_ops import analyse
from workbench import batch_snapshot


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.QualityTests("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def run_case(self, day="2026-06-30", folder="review"):
        return analyse(self.fixture.inputs, self.fixture.root / folder, day)

    def test_followup_includes_due_today_and_future_completions_without_leakage(self):
        result = self.run_case()
        rows = {r["action_id"]:r for r in result["operations"]["queue"]}
        self.assertEqual({k:r["snapshot_status"] for k,r in rows.items()},
                         {"A1":"overdue","A2":"due_today","A3":"due_soon","A5":"overdue"})
        self.assertEqual(rows["A1"]["completed_on_source"], "2026-07-01")
        self.assertEqual(rows["A2"]["days_until_due"], 0)
        self.assertEqual(result["operations"]["metrics"], {"outstanding_actions":4,"due_today":1,"due_soon":1,"closed_parent_followup":0})
        self.assertNotIn("A6", {r["action_id"] for r in result["operations"]["actions"]})
        july = self.run_case("2026-07-31", "july")
        followup = {r["action_id"] for r in july["operations"]["queue"] if r["closed_parent_followup"]}
        self.assertEqual(followup, {"A2","A3"})
        self.assertEqual(july["operations"]["metrics"]["closed_parent_followup"], 2)

    def test_seven_day_boundary_and_not_yet_created_action(self):
        self.fixture.data["actions"] += [
            ["A7","D4","QA","2026-06-21","2026-07-07",None],
            ["A8","D4","QA","2026-06-21","2026-07-08",None],
            ["A9","D4","QA","2026-07-01","2026-07-02",None]]
        self.fixture.save()
        rows = {r["action_id"]:r for r in self.run_case()["operations"]["queue"]}
        self.assertEqual(rows["A7"]["snapshot_status"], "due_soon")
        self.assertEqual(rows["A8"]["snapshot_status"], "later")
        self.assertNotIn("A9", rows)

    def test_age_bands_are_exhaustive_and_boundary_correct(self):
        for age in (0,7,8,30,31,60,61):
            opened = (date(2026,6,30)-timedelta(days=age)).isoformat()
            self.fixture.data["deviations"].append([f"AGE{age}","B1","age-fixture",opened,None])
        self.fixture.save()
        result = self.run_case()
        row = next(r for r in result["operations"]["aging"] if r["category"] == "age-fixture")
        self.assertEqual([row[k] for k in ("age_0_7","age_8_30","age_31_60","age_61_plus")], [2,2,2,1])
        self.assertEqual(row["oldest_open_days"], 61)
        self.assertEqual(sum(r["open_records"] for r in result["operations"]["aging"]), result["metrics"]["open_deviations"])

    def test_monthly_flow_includes_same_day_closure_and_partial_month(self):
        self.fixture.data["deviations"].append(["D5","B1","same-day","2026-06-01","2026-06-01"])
        self.fixture.save()
        result = self.run_case("2026-07-14")
        rows = result["operations"]["monthly"]
        self.assertEqual(rows[0], {"period":"2026-06","period_end":"2026-06-30","opening_open":0,
                                  "opened_in_period":4,"closed_in_period":2,"ending_open":2})
        self.assertEqual(rows[1], {"period":"2026-07","period_end":"2026-07-14","opening_open":2,
                                  "opened_in_period":1,"closed_in_period":0,"ending_open":3})
        for row in rows:
            self.assertEqual(row["opening_open"]+row["opened_in_period"]-row["closed_in_period"], row["ending_open"])

    def test_twelve_month_cap_preserves_older_backlog(self):
        self.fixture.data["batches"].append(["B3","Old-demo","2019-01-01"])
        self.fixture.data["deviations"].append(["DOLD","B3","older","2020-01-01",None])
        self.fixture.save()
        rows = self.run_case("2026-07-31")["operations"]["monthly"]
        self.assertEqual(len(rows),12)
        self.assertEqual(rows[0]["period"],"2025-08")
        self.assertEqual(rows[0]["opening_open"],1)
        self.assertEqual(rows[-1]["ending_open"],3)

    def test_batch_trace_uses_fixed_snapshot_and_retains_completed_actions(self):
        result = self.run_case()
        batch = batch_snapshot(result,"B1")
        self.assertEqual(len(batch["measurements"]),5)
        self.assertEqual({r["deviation_id"] for r in batch["deviations"]},{"D1","D2","D4"})
        self.assertEqual({r["action_id"] for r in batch["actions"]},{"A1","A2","A3","A4","A5"})
        self.assertEqual(next(r for r in batch["actions"] if r["action_id"] == "A4")["snapshot_status"],"completed")
        self.assertIsNone(next(r for r in batch["actions"] if r["action_id"] == "A4")["days_until_due"])
        self.fixture.data["test_results"][2][4] = 100
        self.fixture.save()
        self.assertEqual(next(r for r in batch_snapshot(result,"B1")["measurements"] if r["test_id"] == "T3")["value"],106)
        with self.assertRaises(ValueError):
            batch_snapshot(result,"B2")

    def test_html_export_escapes_source_text_and_preserves_hashes(self):
        self.fixture.data["batches"][0][1] = '<script>alert("x")</script>'
        self.fixture.save()
        result = self.run_case()
        html = (self.fixture.root/"review/QUALITY_REVIEW.html").read_text(encoding="utf-8")
        self.assertNotIn('<script>',html)
        self.assertIn('&lt;script&gt;',html)
        for filename in ("review_queue.csv","review_aging.csv","review_monthly.csv","QUALITY_REVIEW.html"):
            self.assertIn(filename,result["artifact_sha256"])

    def test_empty_history_and_latest_supported_date(self):
        early = self.run_case("2025-12-31")
        self.assertEqual(early["operations"]["queue"],[])
        self.assertEqual(early["operations"]["monthly"],[])
        self.assertEqual(early["operations"]["batches"],[])
        late = self.run_case("9999-12-31","late")
        self.assertEqual(late["operations"]["monthly"][-1]["period_end"],"9999-12-31")

    def test_frozen_output_is_persistent_and_not_resource_directory(self):
        with patch.object(runtime_paths.sys,"frozen",True,create=True), patch.dict(os.environ,{"LOCALAPPDATA":str(self.fixture.root)}):
            expected = self.fixture.root/"BatchScope/outputs"
            self.assertEqual(runtime_paths.output_root(Path("temporary-resources")),expected)
        self.assertEqual(runtime_paths.output_root(self.fixture.root),self.fixture.root/"outputs")
