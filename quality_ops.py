"""BatchScope: synthetic pharmaceutical quality operations, using the standard library."""
from __future__ import annotations

import argparse
import csv
from contextlib import closing
from datetime import date, timedelta, datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import random
import re
import sqlite3
from runtime_paths import RESOURCE_ROOT
from workbench import build_operations, export_operations

ROOT = RESOURCE_ROOT
VERSION = "0.7.0-alpha.4"
COLUMNS = {
    "batches": "batch_id product manufactured_on".split(),
    "test_results": "test_id batch_id test_type method value unit spec_low spec_high spec_unit measured_on".split(),
    "deviations": "deviation_id batch_id category opened_on closed_on".split(),
    "actions": "action_id deviation_id owner_role created_on due_on completed_on".split(),
}
DATE_FIELDS = {"manufactured_on", "measured_on", "opened_on", "closed_on", "created_on", "due_on", "completed_on"}
OPTIONAL = {"value", "closed_on", "completed_on"}
NUMBERS = {"value", "spec_low", "spec_high"}
NUMBER_RE = re.compile(r'^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$')
INPUT_FINDING_COLUMNS = ['table', 'row', 'field', 'level', 'value', 'reference_value', 'reason', 'related_row']


def finite_number(value):
    """Decimal/exponent values only; never guess separators or strip units."""
    if isinstance(value, bool) or not NUMBER_RE.fullmatch(str(value).strip()):
        raise ValueError('Use a finite number without separators or unit text.')
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('Use a finite number without separators or unit text.')
    # Inspect the decimal mantissa so even very long exponents cannot hide underflow.
    if number == 0 and any(digit in '123456789' for digit in str(value).lower().split('e', 1)[0]):
        raise ValueError('Non-zero value is too small to store; it would become zero.')
    return number


def iso_date(value):
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("Use YYYY-MM-DD dates.")
    return parsed


def write_csv(path, columns, rows):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        for row in rows:
            # CSV spreadsheets must not interpret user-supplied text as formulas.
            writer.writerow(["'" + x if isinstance(x, str) and x.lstrip().startswith(("=", "+", "-", "@"))
                             else x for x in row])


def generate(folder, seed=42, batches=100):
    """Stable dates and a fixed seed make the same inputs byte-reproducible."""
    folder = Path(folder)
    if folder.exists():
        raise ValueError("Input folder already exists; choose a new folder.")
    if not 1 <= batches <= 10000:
        raise ValueError("Choose between 1 and 10000 batches.")
    rng = random.Random(seed)
    data = {table: [] for table in COLUMNS}
    start = date(2026, 1, 1)
    for i in range(1, batches + 1):
        batch = f"B{i:04d}"
        made = start + timedelta(days=rng.randrange(180))
        product = "Demo-Tablet" if i % 2 else "Demo-Injectable"
        data["batches"].append([batch, product, made.isoformat()])
        for j, (test, low, high) in enumerate((("assay", 95.0, 105.0), ("purity", 98.0, 100.0))):
            value = None if i % 13 == 0 else round(rng.uniform(low - 1.5, high + 1.5), 2)
            data["test_results"].append([f"T{i:04d}-{j}", batch, test, "demo-HPLC", value,
                                         "%", low, high, "%", (made + timedelta(days=2)).isoformat()])
        if i % 3 == 0:
            dev = f"D{i:04d}"
            opened = made + timedelta(days=3)
            closed = None if i % 2 else (opened + timedelta(days=rng.randrange(5, 45))).isoformat()
            data["deviations"].append([dev, batch, "laboratory" if i % 2 else "documentation", opened.isoformat(), closed])
            for j in range(2):
                created = opened + timedelta(days=j)
                due = created + timedelta(days=14 + 7*j)
                completed = None if (i+j) % 3 else (due + timedelta(days=rng.randrange(-4, 25))).isoformat()
                data["actions"].append([f"A{i:04d}-{j}", dev, "QA" if j else "QC", created.isoformat(), due.isoformat(), completed])
    folder.mkdir(parents=True)
    for table, rows in data.items():
        write_csv(folder / f"{table}.csv", COLUMNS[table], rows)
    (folder / "SOURCE.json").write_text(json.dumps({
        "data_type": "synthetic", "generator_version": VERSION, "seed": seed,
        "batches": batches, "date_origin": start.isoformat(),
        "note": "Fictional products, methods and specifications; no real patient, employee or company records."
    }, indent=2), encoding="utf-8")
    return {table: len(rows) for table, rows in data.items()}


def load_inputs(folder, contents=None):
    """Fail closed on structural/domain input errors; missing measurements are retained."""
    data, issues = {}, []
    def issue(table, row, field, reason):
        issues.append([table, row, field, reason])

    for table, columns in COLUMNS.items():
        data[table] = []
        seen = set()
        try:
            content = ((Path(folder) / f'{table}.csv').read_bytes() if contents is None
                       else contents.get(f'{table}.csv'))
            if content is None:
                raise OSError('Missing or unreadable file')
            text = content.decode('utf-8-sig')
        except (OSError, UnicodeError):
            issue(table, 1, 'file', 'File is missing, unreadable or not UTF-8.')
            continue
        with io.StringIO(text, newline='') as handle:
            reader = csv.DictReader(handle, strict=True)
            try:
                found_headers = reader.fieldnames
                records = list(reader) if found_headers == columns else []
            except csv.Error as exc:
                issue(table, max(reader.line_num, 1), 'csv', f'Malformed CSV: {exc}')
                continue
            if found_headers != columns:
                issue(table, 1, "header", "Expected exact documented columns and order.")
                continue
            for line, row in enumerate(records, 2):
                if None in row or None in row.values():
                    issue(table, line, "row", "Incorrect number of cells.")
                    continue
                clean = {k: v.strip() for k, v in row.items()}
                for key, value in list(clean.items()):
                    if not value:
                        if key in OPTIONAL:
                            clean[key] = None
                        else:
                            issue(table, line, key, "Required value missing.")
                        continue
                    try:
                        if key in DATE_FIELDS:
                            iso_date(value)
                        elif key in NUMBERS:
                            clean[key] = finite_number(value)
                    except ValueError as exc:
                        issue(table, line, key, 'Use YYYY-MM-DD.' if key in DATE_FIELDS else
                              str(exc))
                pk = clean[columns[0]]
                if pk in seen:
                    issue(table, line, columns[0], "Duplicate primary key.")
                seen.add(pk)
                data[table].append((line, clean))
    if issues:
        return data, issues
    batches = {r["batch_id"]: r for _, r in data["batches"]}
    deviations = {r["deviation_id"]: r for _, r in data["deviations"]}
    if not batches:
        issue("batches", 1, "batch_id", "At least one batch is required.")
    for table in ("test_results", "deviations", "actions"):
        for line, row in data[table]:
            if table == "actions":
                parent = deviations.get(row["deviation_id"])
                start, end = "created_on", "completed_on"
                if parent and row[start] < parent["opened_on"]:
                    issue(table, line, start, "Action predates deviation opening.")
                if row["due_on"] < row[start]:
                    issue(table, line, "due_on", "Due date predates action creation.")
            else:
                parent = batches.get(row["batch_id"])
                start, end = ("measured_on", None) if table == "test_results" else ("opened_on", "closed_on")
                if parent and row[start] < parent["manufactured_on"]:
                    issue(table, line, start, "Event predates batch manufacture.")
            if parent is None:
                field = 'deviation_id' if table == 'actions' else 'batch_id'
                target = 'deviations.csv' if table == 'actions' else 'batches.csv'
                issue(table, line, field, f'Identifier was not found in {target}.')
            if end and row[end] is not None and row[end] < row[start]:
                issue(table, line, end, "Completion/closure predates creation/opening.")
            if table == "test_results":
                if row["unit"] != row["spec_unit"]:
                    issue(table, line, "unit", "Result and specification units differ; no automatic conversion.")
                if row["spec_low"] > row["spec_high"]:
                    issue(table, line, "spec_low", "Lower specification exceeds upper specification.")
    return data, issues


def range_findings(data):
    """Compare like measurements, without treating any observed range as approved."""
    products = {row['batch_id']: row['product'] for _, row in data['batches']}
    groups = {}
    for number, row in data['test_results']:
        key = (products[row['batch_id']], row['test_type'], row['method'], row['unit'], row['spec_unit'])
        groups.setdefault(key, []).append((number, row))
    findings = []
    for rows in groups.values():
        representatives = {}
        for number, row in rows:
            representatives.setdefault((row['spec_low'], row['spec_high']), number)
        if len(representatives) < 2:
            continue
        first, second = list(representatives)[:2]
        for number, row in rows:
            own_range = (row['spec_low'], row['spec_high'])
            other_range = second if own_range == first else first
            findings.append({
                'table': 'test_results', 'row': number, 'field': 'spec_low/spec_high', 'level': 'warning',
                'value': str(own_range[0]) + ' .. ' + str(own_range[1]),
                'reference_value': str(other_range[0]) + ' .. ' + str(other_range[1]),
                'reason': 'Different ranges occur for the same product, test, method and unit; check which specification applies.',
                'related_row': representatives[other_range],
            })
    return findings


def check_inputs(folder):
    """Read once and return findings plus the exact validated data for analysis."""
    folder = Path(folder)
    contents, findings = {}, []
    for name in [f'{table}.csv' for table in COLUMNS] + ['SOURCE.json']:
        try:
            contents[name] = (folder / name).read_bytes()
        except OSError:
            pass  # The loader/marker check below records every unreadable file.
    source_issue = None
    try:
        marker = json.loads(contents.get('SOURCE.json', b'').decode('utf-8-sig'))
        if not isinstance(marker, dict) or marker.get('data_type') != 'synthetic':
            source_issue = 'SOURCE.json must declare data_type as synthetic.'
    except (UnicodeError, ValueError):
        source_issue = 'SOURCE.json is missing, unreadable or invalid JSON.'
    data, issues = load_inputs(folder, contents=contents)
    if source_issue:
        issues.insert(0, ['SOURCE.json', 1, 'data_type', source_issue])
    by_row = {table: dict(rows) for table, rows in data.items()}
    for table, row, field, reason in issues:
        record = by_row.get(table, {}).get(row, {})
        value = record.get(field)
        findings.append({'table': table, 'row': row, 'field': field, 'level': 'error',
                         'value': '' if value is None else str(value), 'reason': reason, 'related_row': None})
    seen = {}
    for number, row in data['test_results']:
        if row['value'] is None:
            findings.append({'table': 'test_results', 'row': number, 'field': 'value', 'level': 'info',
                             'value': '', 'reason': 'Result is missing, not zero.', 'related_row': None})
        key = tuple(row[column] for column in COLUMNS['test_results'][1:])
        if key in seen and row['test_id'] != seen[key][1]:
            findings.append({'table': 'test_results', 'row': number, 'field': 'test_id', 'level': 'warning',
                             'value': row['test_id'], 'reason': 'Same measurement content under a different ID; check duplicate entry or planned repeat.',
                             'related_row': seen[key][0]})
        else:
            seen.setdefault(key, (number, row['test_id']))
    if not issues:
        findings.extend(range_findings(data))
    for finding in findings:
        finding.setdefault('reference_value', '')
    counts = {level: sum(row['level'] == level for row in findings) for level in ('error', 'warning', 'info')}
    profiles = [{'table': table, 'readable_records': len(rows),
                 'missing_results': sum(row['value'] is None for _, row in rows) if table == 'test_results' else None}
                for table, rows in data.items()]
    return {'source': str(folder.resolve()), 'input_sha256': {name: hashlib.sha256(content).hexdigest() for name, content in contents.items()},
            'checked_at_utc': datetime.now(timezone.utc).isoformat(),
            'can_analyse': not counts['error'], 'counts': counts, 'profiles': profiles, 'findings': findings,
            'note': 'Checks describe captured bytes, not current live files. Warnings are review prompts; no data is corrected or deleted.',
            '_data': data}


def input_report(check):
    return {key: value for key, value in check.items() if key != '_data'}


def write_input_report(check, folder):
    folder = Path(folder)
    (folder / 'INPUT_CHECK.json').write_text(json.dumps(input_report(check), ensure_ascii=False, indent=2), encoding='utf-8')
    columns = INPUT_FINDING_COLUMNS
    write_csv(folder / 'INPUT_FINDINGS.csv', columns, [[row[key] for key in columns] for row in check['findings']])


def analyse(inputs, output, as_of):
    iso_date(as_of)
    inputs, output = Path(inputs), Path(output)
    if output.exists():
        raise ValueError("Output folder exists; choose a new folder to preserve previous runs.")
    checked = check_inputs(inputs)
    data, hashes = checked['_data'], checked['input_sha256']
    issues = [[row['table'], row['row'], row['field'], row['reason']]
              for row in checked['findings'] if row['level'] == 'error']
    marker_errors = [row for row in issues if row[0] == 'SOURCE.json']
    if marker_errors:
        raise ValueError(marker_errors[0][3])
    output.mkdir(parents=True)
    write_input_report(checked, output)
    if issues:
        write_csv(output / "INPUT_ISSUES.csv", ["table", "row", "field", "reason"], issues)
        (output / "STOPPED.md").write_text("Input validation failed. No analysis produced. / 输入校验失败，未生成分析。\n", encoding="utf-8")
        raise ValueError(f"{len(issues)} input issues; inspect {output / 'INPUT_ISSUES.csv'}")
    reports, details = {}, {}
    with closing(sqlite3.connect(output / "quality.sqlite")) as db:
        db.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
        for table, columns in COLUMNS.items():
            db.executemany(f"INSERT INTO {table} VALUES ({','.join('?' for _ in columns)})",
                           [[r[c] for c in columns] for _, r in data[table]])
        for query in sorted((ROOT / "sql").glob("*.sql")):
            cursor = db.execute(query.read_text(encoding="utf-8"), {"as_of": as_of})
            columns = [c[0] for c in cursor.description]
            rows = cursor.fetchall()
            if any(isinstance(x, float) and not math.isfinite(x) for row in rows for x in row):
                raise ValueError("Numeric aggregation overflow; partial outputs must not be used.")
            reports[query.stem] = [dict(zip(columns, row)) for row in rows]
            write_csv(output / f"{query.stem}.csv", columns, rows)
        for query in sorted((ROOT / "detail_sql").glob("*.sql")):
            cursor = db.execute(query.read_text(encoding="utf-8"), {"as_of": as_of})
            columns = [c[0] for c in cursor.description]
            rows = cursor.fetchall()
            details[query.stem] = [dict(zip(columns, row)) for row in rows]
            write_csv(output / f"{query.stem}_details.csv", columns, rows)
        operations = build_operations(db, as_of)
        db.commit()
    tests = reports["01_test_ranges"]
    metrics = {
        "measured_records": sum(r["measured_records"] for r in tests),
        "judgeable_records": sum(r["judgeable_records"] for r in tests),
        "missing_records": sum(r["missing_records"] for r in tests),
        "outside_range_records": sum(r["outside_range_records"] for r in tests),
        "open_deviations": sum(r["open_records"] for r in reports["02_deviation_backlog"]),
        "overdue_actions": len(reports["03_overdue_actions"]),
    }
    summary = {"project": "BatchScope", "version": VERSION, "as_of": as_of, "data_type": "synthetic-demo-only",
               "input_rows": {t: len(rows) for t, rows in data.items()},
               "input_sha256": hashes, "metrics": metrics, "reports": reports,
               "details": details, "operations": operations}
    export_operations(output, summary)
    (output / "RESULTS.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    lines = ["# BatchScope / 批次质量洞察", "", "Pharmaceutical quality operations analytics / 药企质量运营分析", "", "Synthetic demonstration / 模拟数据演示",
             f"As of / 截至：{as_of}", "", "| Metric / 指标 | Value / 数值 |", "|---|---:|"]
    labels = {"measured_records": "Measured records / 检验记录", "judgeable_records": "Judgeable / 可判定记录",
              "missing_records": "Missing results / 缺失结果", "outside_range_records": "Outside example range / 超出示例范围",
              "open_deviations": "Open deviations / 未关闭偏差", "overdue_actions": "Overdue actions / 逾期措施"}
    lines += [f"| {labels[k]} | {v} |" for k, v in metrics.items()]
    lines += ["", "Missing measurements are not zero and are excluded from the range-rate denominator. Future events are excluded; future closures/completions remain open at this date. Due today is not overdue.",
              "缺失结果不是零，不进入范围异常率分母。排除未来发生的事件；未来才关闭/完成的记录在本日期仍未完成。今天到期不算逾期。",
              "", "Configured bounds are fictional examples. Flags are review prompts, not OOS investigations, regulatory standards, batch release or validated GMP/CSV software.",
              "范围为虚构示例；标记是复核提示，不代表 OOS 调查结论、法规标准、批次放行或经过 GMP/CSV 验证的软件。"]
    (output / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary["artifact_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file()}
    # A completion manifest is written last; partial output folders are not completed runs.
    (output / "manifest.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("folder", type=Path)
    gen.add_argument("--seed", type=int, default=42)
    gen.add_argument("--batches", type=int, default=100)
    run = sub.add_parser("analyse")
    run.add_argument("inputs", type=Path)
    run.add_argument("output", type=Path)
    run.add_argument("--as-of", required=True)
    args = parser.parse_args()
    try:
        result = generate(args.folder, args.seed, args.batches) if args.command == "generate" else analyse(args.inputs, args.output, args.as_of)["metrics"]
    except (OSError, ValueError, sqlite3.Error, UnicodeError) as exc:
        parser.exit(1, f"Failed / 失败：{exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
