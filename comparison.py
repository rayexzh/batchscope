"""BatchScope: compare two as-of dates using one validated input snapshot."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3

from quality_ops import ROOT, VERSION, analyse, iso_date, write_csv


def snapshot(db, as_of):
    reports, details = {}, {}
    for directory, target in (("sql", reports), ("detail_sql", details)):
        for query in sorted((ROOT / directory).glob("*.sql")):
            cursor = db.execute(query.read_text(encoding="utf-8"), {"as_of": as_of})
            columns = [c[0] for c in cursor.description]
            target[query.stem] = [dict(zip(columns, row)) for row in cursor.fetchall()]
    tests = reports["01_test_ranges"]
    metrics = {key: sum(row[key] for row in tests) for key in
               ("measured_records", "judgeable_records", "missing_records", "outside_range_records")}
    metrics["open_deviations"] = sum(r["open_records"] for r in reports["02_deviation_backlog"])
    metrics["overdue_actions"] = len(reports["03_overdue_actions"])
    return {"as_of": as_of, "metrics": metrics, "reports": reports, "details": details}


def action_status(row, day):
    if row["created_on"] > day:
        return "not_created"
    if row["completed_on_source"] and row["completed_on_source"] <= day:
        return "completed"
    return "overdue" if row["due_on"] < day else "not_due"


def build_comparison(db, before, after):
    start, end = before["as_of"], after["as_of"]
    metrics = [{"metric": key, "before_value": value,
                "after_value": after["metrics"][key], "delta": after["metrics"][key] - value}
               for key, value in before["metrics"].items()]
    earlier_tests = {r["test_id"] for r in before["details"]["01_test_ranges"]}
    tests = [{**row, "change": "new_measurement"} for row in after["details"]["01_test_ranges"]
             if row["test_id"] not in earlier_tests]
    earlier_devs = {r["deviation_id"]: r for r in before["details"]["02_deviation_backlog"]}
    deviations = []
    for row in after["details"]["02_deviation_backlog"]:
        previous = earlier_devs.get(row["deviation_id"])
        old = previous["snapshot_status"] if previous else "not_opened"
        new = row["snapshot_status"]
        if old == "closed":
            continue
        change = {("not_opened", "open"): "opened_still_open",
                  ("not_opened", "closed"): "opened_and_closed",
                  ("open", "closed"): "closed_since_start",
                  ("open", "open"): "still_open"}[(old, new)]
        deviations.append({**row, "before_status": old, "after_status": new, "change": change})
    earlier_actions = {r["action_id"] for r in before["details"]["03_overdue_actions"]}
    later_actions = {r["action_id"] for r in after["details"]["03_overdue_actions"]}
    cursor = db.execute("""SELECT a.action_id, a.deviation_id, d.batch_id, b.product,
        d.category, a.owner_role, a.created_on, a.due_on, a.completed_on AS completed_on_source
        FROM actions a JOIN deviations d USING(deviation_id) JOIN batches b USING(batch_id)
        ORDER BY a.action_id""")
    columns = [c[0] for c in cursor.description]
    actions = []
    for values in cursor.fetchall():
        row = dict(zip(columns, values))
        key = row["action_id"]
        if key not in earlier_actions | later_actions:
            continue
        change = ("still_overdue" if key in earlier_actions & later_actions else
                  "newly_overdue" if key in later_actions else "resolved_overdue")
        actions.append({**row, "before_status": action_status(row, start),
                        "after_status": action_status(row, end), "change": change,
                        "before_overdue_days": (iso_date(start) - iso_date(row["due_on"])).days if key in earlier_actions else None,
                        "after_overdue_days": (iso_date(end) - iso_date(row["due_on"])).days if key in later_actions else None})
    return {"from_date": start, "to_date": end, "metrics": metrics,
            "deviations": deviations, "actions": actions, "measurements": tests}


def compare(inputs, output, from_date, to_date):
    if iso_date(from_date) > iso_date(to_date):
        raise ValueError("Comparison start must be on or before the end date. / 对比起始日期不能晚于截至日期。")
    output = Path(output)
    if output.exists():
        raise ValueError("Output folder exists; choose a new folder to preserve previous runs.")
    # Read/validate source files once; both dates use this database, never re-read CSVs.
    after = analyse(inputs, output / "end_snapshot", to_date)
    uri = (output / "end_snapshot/quality.sqlite").resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        before = snapshot(db, from_date)
        comparison = build_comparison(db, before, after)
    comparison.update(project="BatchScope", version=VERSION, data_type="synthetic-demo-only", input_sha256=after["input_sha256"])
    (output / "START_SNAPSHOT.json").write_text(json.dumps(before, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    (output / "COMPARISON.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    schemas = {"metrics": ["metric", "before_value", "after_value", "delta"],
               "deviations": ["deviation_id", "batch_id", "product", "category", "opened_on", "closed_on_source", "before_status", "after_status", "change"],
               "actions": ["action_id", "deviation_id", "batch_id", "product", "category", "owner_role", "created_on", "due_on", "completed_on_source", "before_status", "after_status", "change", "before_overdue_days", "after_overdue_days"],
               "measurements": ["test_id", "batch_id", "product", "test_type", "method", "value", "unit", "spec_low", "spec_high", "measured_on", "snapshot_status", "change"]}
    for name, columns in schemas.items():
        write_csv(output / f"comparison_{name}.csv", columns, [[row[k] for k in columns] for row in comparison[name]])
    lines = ["# BatchScope: date comparison / 批次质量洞察：日期对比", "", f"{from_date} → {to_date}", "",
             "| Metric / 指标 | Start / 起始 | End / 截至 | Change / 变化 |", "|---|---:|---:|---:|"]
    from ui_text import tr
    lines += [f"| {tr(r['metric'], 'en')} / {tr(r['metric'], 'zh')} | {r['before_value']} | {r['after_value']} | {r['delta']:+d} |" for r in comparison["metrics"]]
    lines += ["", "## Record movements / 记录变化", ""]
    for name in ("deviations", "actions", "measurements"):
        counts = {}
        for row in comparison[name]:
            counts[row["change"]] = counts.get(row["change"], 0) + 1
        lines.append(f"- {name}: " + (", ".join(f"{tr(k, 'en')} / {tr(k, 'zh')}: {v}" for k, v in counts.items()) or "0"))
    lines += ["", "Both dates use one input snapshot. Changes reflect event dates, not edit history or proof of cause. Newly overdue means present at the end but not at the start; it is not a count of all overdue episodes between dates. Opened-and-closed deviations do not increase the ending backlog. Equal dates give zero net changes; continuing records can still be listed.",
              "两个日期使用同一份输入快照。变化依据事件日期，不是编辑历史或原因证明。新增逾期指期末存在、期初不存在的逾期记录，并非期间所有发生过逾期的次数。期间开启并关闭的偏差不增加期末积压。同日对比净变化为零，仍可列出持续未完成记录。",
              "", "Synthetic demonstration only; no batch-release or compliance decisions. / 仅模拟演示，不能用于批次放行或合规判断。"]
    (output / "COMPARISON.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    comparison["artifact_sha256"] = {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in sorted(output.rglob("*")) if p.is_file()}
    (output / "manifest.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    # Main view stays an end-date snapshot; the comparison window owns separate data.
    return {**after, "comparison": comparison}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--from", dest="from_date", required=True)
    parser.add_argument("--to", dest="to_date", required=True)
    args = parser.parse_args()
    try:
        result = compare(args.inputs, args.output, args.from_date, args.to_date)
    except (OSError, ValueError, sqlite3.Error, UnicodeError) as exc:
        parser.exit(1, f"Failed / 失败：{exc}\n")
    print(json.dumps(result["comparison"]["metrics"], indent=2))
