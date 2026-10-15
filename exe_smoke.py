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
        checker = window.open_inputcheck()
        checker.window.withdraw()
        checker.buttons['check'].invoke()
        deadline = time.monotonic() + 60
        while checker.busy and time.monotonic() < deadline:
            root.update();time.sleep(.03)
        if checker.busy or not checker.result or checker.result['counts']['error']:
            raise AssertionError('Packaged input check did not accept generated data.')
        if len(checker.result['profiles']) != 4 or checker.result['counts']['info'] != 14:
            raise AssertionError('Packaged input check did not retain missing measurements.')
        if window.result is not None:
            raise AssertionError('Checking input files must not start the main analysis.')
        from input_check_ui import export_check
        export_check(checker.result, folder / 'input-check-export')
        if not (folder / 'input-check-export/manifest.json').is_file():
            raise AssertionError('Packaged input check export did not finish.')
        from quality_ops import check_inputs, COLUMNS
        import csv
        bad_inputs = folder / 'bad-inputs'
        bad_inputs.mkdir()
        for source in inputs.iterdir():
            if source.is_file():
                (bad_inputs / source.name).write_bytes(source.read_bytes())
        with (bad_inputs / 'test_results.csv').open(encoding='utf-8-sig', newline='') as handle:
            rows = list(csv.reader(handle))
        rows[1][COLUMNS['test_results'].index('value')] = '1_00'
        with (bad_inputs / 'test_results.csv').open('w', encoding='utf-8-sig', newline='') as handle:
            csv.writer(handle).writerows(rows)
        bad_check = check_inputs(bad_inputs)
        if bad_check['can_analyse'] or not any(r['row'] == 2 and r['value'] == '1_00' for r in bad_check['findings']):
            raise AssertionError('Packaged numeric check silently accepted an underscore.')
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
        from audit_trail import inspect_audit_csv
        if inspect_audit_csv(audit.path)['diagnostic'] is not None:
            raise AssertionError('Packaged audit import format check rejected its own sample.')
        mismatched=folder/'wrong-audit-header.csv'
        mismatched.write_text('event_id,timestamp,comment\n',encoding='utf-8')
        if 'Missing columns' not in (inspect_audit_csv(mismatched)['diagnostic'] or ''):
            raise AssertionError('Packaged audit import format check did not explain missing fields.')
        audit.table.tree.selection_set('0')
        editor=audit.annotate()
        editor.window.withdraw()
        editor.reviewer.set('Demo QA')
        editor.status.current(2)
        editor.note.insert('1.0','Request original correction evidence')
        if not editor.save():raise AssertionError('Packaged note save failed.')
        editor.window.deiconify();editor.window.geometry('700x500');root.update()
        editor.canvas.yview_moveto(1);root.update()
        top=editor.canvas.winfo_rooty()
        if (not editor.save_button.winfo_ismapped()
                or editor.history_text.winfo_rooty()<top
                or editor.history_text.winfo_rooty()+editor.history_text.winfo_height()>top+editor.canvas.winfo_height()):
            raise AssertionError('Packaged note history or save action is clipped at minimum size.')
        editor.window.withdraw()
        fixed_log=audit.path
        audit.load(fixed_log)
        if audit.table.rows[0]['review_status']!='follow_up':
            raise AssertionError('Packaged review notes did not reopen.')
        from audit_trail import export_audit
        export_audit(audit.result, folder/'audit-export',audit.store.bundle(audit.result))
        if not (folder/'audit-export/review-notes.json').exists():
            raise AssertionError('Packaged review annotation export failed.')
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
        laboratory = window.open_laboratory()
        if laboratory is None:
            raise AssertionError('Packaged laboratory did not open from completed snapshot.')
        laboratory.window.withdraw()
        selected = laboratory.model.tests[0]
        original_value = selected['value']
        midpoint = selected['spec_low'] / 2 + selected['spec_high'] / 2
        laboratory.fields['value'].set(str(midpoint))
        laboratory.buttons['stage'].invoke()
        laboratory.buttons['run'].invoke()
        deadline = time.monotonic() + 60
        while laboratory.busy and time.monotonic() < deadline:
            root.update();time.sleep(.01)
        if laboratory.busy or not laboratory.result:
            raise AssertionError('Packaged laboratory scenario did not finish.')
        if laboratory.result['baseline_metrics'] != expected:
            raise AssertionError('Laboratory baseline differs from the original snapshot.')
        laboratory.reason.set('Preset synthetic exercise')
        for fields in laboratory.repeat_fields:
            fields['value'].set(str(midpoint))
        laboratory.buttons['evaluate'].invoke()
        deadline = time.monotonic() + 60
        while laboratory.busy and time.monotonic() < deadline:
            root.update();time.sleep(.01)
        if laboratory.busy or not laboratory.rechecks or len(laboratory.repeat_table.rows) != 3:
            raise AssertionError('Packaged repeat exercise failed.')
        if laboratory.repeat_table.rows[0]['value'] != original_value:
            raise AssertionError('Repeat exercise replaced the initial result.')
        experiment = dict(laboratory.result, rechecks=laboratory.rechecks)
        laboratory.model.export(experiment, folder/'laboratory-export')
        if not (folder/'laboratory-export/manifest.json').is_file():
            raise AssertionError('Packaged laboratory export did not complete.')
        laboratory.reset()
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
                              "read-only audit CSV header inspection",
                              "multi-date quality snapshots and movement exports",
                              "review note save, reopen and full export",
                              "review note history at minimum window size",
                              "isolated laboratory comparison and unchanged baseline",
                              "three-attempt practice retaining initial result",
                              "replayable laboratory exports and reset",
                              "input check before analysis and retained missing results",
                              "ambiguous numeric input rejected with row evidence",
                              "full bilingual input-check export and manifest"],
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
