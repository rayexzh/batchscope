"""Production-bundle smoke check: resources, calculations and native GUI flows."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import traceback
import time


def self_test(folder):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    root = None
    previous_local = os.environ.get("LOCALAPPDATA")
    try:
        os.environ["LOCALAPPDATA"] = str(folder / "test-profile")
        from quality_ops import analyse, generate, VERSION
        from comparison import compare
        from runtime_paths import output_root
        inputs = folder / "inputs"
        generate(inputs)
        result = analyse(inputs, folder / "analysis", "2026-06-30")
        expected = {"measured_records":198,"judgeable_records":184,"missing_records":14,
                    "outside_range_records":74,"open_deviations":22,"overdue_actions":30}
        if result["metrics"] != expected:
            raise AssertionError("June metrics differ from independently expected fixture.")
        later = compare(inputs, folder / "comparison", "2026-06-30", "2026-07-31")
        if later["metrics"]["open_deviations"] != 17 or later["metrics"]["overdue_actions"] != 33:
            raise AssertionError("July snapshot mismatch.")
        operations = result["operations"]
        if sum(r["snapshot_status"] == "overdue" for r in operations["queue"]) != 30:
            raise AssertionError("Work queue does not reconcile with original overdue metric.")
        if sum(r["open_records"] for r in operations["aging"]) != 22:
            raise AssertionError("Backlog age does not reconcile.")
        for name, digest in result["artifact_sha256"].items():
            if hashlib.sha256((folder / "analysis" / name).read_bytes()).hexdigest() != digest:
                raise AssertionError("Artifact hash mismatch.")
        with closing(sqlite3.connect(folder / "analysis/quality.sqlite")) as db:
            if db.execute("PRAGMA foreign_key_check").fetchall():
                raise AssertionError("Foreign key errors.")
        import tkinter as tk
        from app import Window
        from ui_theme import enable_dpi_awareness
        enable_dpi_awareness()
        root = tk.Tk()
        root.withdraw()
        window = Window(root)
        window.create_data()
        window.as_of.set("2026-06-30")
        window.start()
        deadline = time.monotonic() + 60
        while window.busy and time.monotonic() < deadline:
            root.update()
            time.sleep(.03)
        if window.busy or window.phase != "completed" or window.result["metrics"] != expected:
            raise AssertionError("Generate/Analyse desktop workflow failed.")
        if not window.output.is_relative_to(output_root()):
            raise AssertionError("Desktop output escaped the persistent output root.")
        original_inputs = window.inputs.get()
        original_result = window.result
        window.inputs.set(str(folder / "not-yet-analysed"))
        if "尚未重新分析" not in window.status.get() or window.result is not original_result:
            raise AssertionError("Changed inputs must label and retain the previous snapshot.")
        window.inputs.set(original_inputs)
        if "尚未重新分析" in window.status.get():
            raise AssertionError("Restored inputs should clear the pending-input notice.")
        window.result, window.output, window.phase = result, folder / "analysis", "completed"
        window.apply_view()
        view = window.open_workbench()
        view.window.withdraw()
        if not view.visible_rows["queue"]:
            raise AssertionError("Empty review queue.")
        view.tables["queue"].tree.selection_set("0")
        batch = view.open_batch()
        batch.window.withdraw()
        if not batch.result["actions"]:
            raise AssertionError("No batch actions in batch view.")
        audit = window.open_audit()
        audit.window.withdraw()
        audit.generate()
        if not audit.result or audit.result['affected_events'] != 4:
            raise AssertionError('Packaged audit review failed.')
        from audit_trail import export_audit
        export_audit(audit.result, folder/'audit-export')
        audit_dates = audit.timeline()
        audit_dates.window.withdraw()
        audit_dates.dates.set('2026-06-28,2026-06-29,2026-06-30')
        audit_dates.start()
        deadline = time.monotonic()+60
        while audit_dates.busy and time.monotonic()<deadline:
            root.update();time.sleep(.03)
        if not audit_dates.result or len(audit_dates.result['unplaced']) != 1:
            raise AssertionError('Packaged audit timeline failed.')
        timeline = window.open_timeline()
        timeline.window.withdraw()
        timeline.dates.set('2026-05-31,2026-06-30,2026-07-31')
        timeline.start()
        deadline = time.monotonic()+60
        while timeline.busy and time.monotonic()<deadline:
            root.update();time.sleep(.03)
        if not timeline.result or [r['open_deviations'] for r in timeline.result['rows'][-2:]] != [22,17]:
            raise AssertionError('Packaged multi-date quality review failed.')
        fixed_id = batch.result["batch"]["batch_id"]
        window.toggle_language()
        window.toggle_theme()
        root.deiconify()
        root.geometry("900x600")
        window.adjust_font(3)
        for _ in range(4): root.update()
        for button in (window.run_button,window.open_button,window.compare_button,window.view_compare_button):
            if not button.winfo_ismapped() or button.winfo_width() < button.winfo_reqwidth():
                raise AssertionError("A date control label is clipped.")
        root.withdraw()
        if batch.result["batch"]["batch_id"] != fixed_id:
            raise AssertionError("Batch changed during presentation switch.")
        window.result = later
        comparison = window.open_comparison()
        comparison.window.withdraw()
        root.update()
        evidence = {"project":"BatchScope","version":VERSION,"status":"passed",
                    "checks":["bundled SQL resources","June and July metrics","two-date comparison",
                              "work queue and backlog reconciliation","SQLite foreign keys","artifact hashes",
                              "native Generate/Analyse workflow and persistent outputs",
                              "native workbench and batch tracing","language/theme switching","comparison window",
                              "changed-input snapshot context", "small-window date controls",
                              "audit generation, review and SQLite export", "audit timeline and undated events",
                              "multi-date quality snapshots and movement exports"],
                    "metrics": result["metrics"], "operations_metrics":operations["metrics"],
                    "persistent_output_root":str(output_root())}
        (folder / "SELF_TEST.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2), encoding="utf-8")
        return 0
    except Exception:
        (folder / "SELF_TEST.json").write_text(json.dumps({"status":"failed","error":traceback.format_exc()},indent=2),encoding="utf-8")
        return 1
    finally:
        if root is not None:
            root.destroy()
        if previous_local is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = previous_local
