"""Transparent work queues, backlog age and reconciled monthly deviation flows."""
from datetime import date, timedelta
from html import escape
from pathlib import Path

from runtime_paths import RESOURCE_ROOT
from review import display_value, field_label


def query_rows(db, sql, params):
    cursor = db.execute(sql, params)
    columns = [c[0] for c in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def monthly_flows(db, as_of):
    first = db.execute("SELECT MIN(opened_on) FROM deviations WHERE opened_on <= ?", (as_of,)).fetchone()[0]
    if first is None:
        return []
    end = date.fromisoformat(as_of)
    # Up to 12 months; initial stock still counts older open records.
    month_index = end.year * 12 + end.month - 1
    lower = max(date.fromisoformat(first).year * 12 + date.fromisoformat(first).month - 1, month_index - 11)
    rows = []
    for index in range(lower, month_index + 1):
        start = date(index // 12, index % 12 + 1, 1)
        finish = end if index == month_index else date((index+1) // 12, (index+1) % 12 + 1, 1) - timedelta(days=1)
        row = query_rows(db, """SELECT
            COALESCE(SUM(CASE WHEN opened_on < :start AND (closed_on IS NULL OR closed_on >= :start) THEN 1 ELSE 0 END),0) AS opening_open,
            COALESCE(SUM(CASE WHEN opened_on BETWEEN :start AND :finish THEN 1 ELSE 0 END),0) AS opened_in_period,
            COALESCE(SUM(CASE WHEN closed_on BETWEEN :start AND :finish THEN 1 ELSE 0 END),0) AS closed_in_period,
            COALESCE(SUM(CASE WHEN opened_on <= :finish AND (closed_on IS NULL OR closed_on > :finish) THEN 1 ELSE 0 END),0) AS ending_open
            FROM deviations WHERE opened_on <= :finish""", {"start": start.isoformat(), "finish": finish.isoformat()})[0]
        if row["opening_open"] + row["opened_in_period"] - row["closed_in_period"] != row["ending_open"]:
            raise ValueError("Monthly backlog reconciliation failed.")
        rows.append({"period": start.strftime("%Y-%m"), "period_end": finish.isoformat(), **row})
    return rows


def build_operations(db, as_of):
    actions = query_rows(db, (RESOURCE_ROOT / "operations_sql/01_actions.sql").read_text(encoding="utf-8"), {"as_of": as_of})
    queue = []
    for action in actions:
        if action["snapshot_status"] != "completed":
            queue.append({**action, "closed_parent_followup": int(action["parent_status"] == "closed")})
    aging = query_rows(db, (RESOURCE_ROOT / "operations_sql/02_aging.sql").read_text(encoding="utf-8"), {"as_of": as_of})
    return {"as_of": as_of, "actions": actions, "queue": queue, "aging": aging,
            "monthly": monthly_flows(db, as_of),
            "batches": query_rows(db, "SELECT * FROM batches WHERE manufactured_on <= :as_of ORDER BY batch_id", {"as_of": as_of}),
            "metrics": {"outstanding_actions": len(queue),
                        "due_today": sum(r["snapshot_status"] == "due_today" for r in queue),
                        "due_soon": sum(r["snapshot_status"] == "due_soon" for r in queue),
                        "closed_parent_followup": sum(r["closed_parent_followup"] for r in queue)}}


def batch_snapshot(result, batch_id):
    operations = result["operations"]
    batch = next((r for r in operations["batches"] if r["batch_id"] == batch_id), None)
    if batch is None:
        raise ValueError("Batch not present in this snapshot.")
    return {"as_of": result["as_of"], "batch": batch,
            "measurements": [r for r in result["details"]["01_test_ranges"] if r["batch_id"] == batch_id],
            "deviations": [r for r in result["details"]["02_deviation_backlog"] if r["batch_id"] == batch_id],
            "actions": [r for r in operations["actions"] if r["batch_id"] == batch_id]}


def export_operations(output, result):
    # Imported at call time to avoid a module cycle.
    from quality_ops import write_csv
    operations = result["operations"]
    schemas = {"queue": "action_id deviation_id batch_id product category owner_role created_on due_on completed_on_source parent_status snapshot_status days_until_due closed_parent_followup".split(),
               "aging": "product category open_records age_0_7 age_8_30 age_31_60 age_61_plus oldest_open_days".split(),
               "monthly": "period period_end opening_open opened_in_period closed_in_period ending_open".split()}
    for name, columns in schemas.items():
        write_csv(Path(output) / f"review_{name}.csv", columns, [[r[c] for c in columns] for r in operations[name]])
    html = ["<!doctype html><html lang='en'><meta charset='utf-8'><title>BatchScope / 批次质量洞察</title>",
            "<style>body{font:16px 'Segoe UI','Microsoft YaHei',sans-serif;background:#edf3f6;color:#18313e;margin:0}main{max-width:1200px;margin:auto;padding:32px}h1,h2{color:#126d78}section{background:white;padding:20px;margin:20px 0;border-radius:8px}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;white-space:nowrap}td,th{padding:10px;text-align:left;border-bottom:1px solid #dce9ee}th{background:#dce9ee}tr:nth-child(even){background:#f1f7fa}.cards{display:flex;gap:12px;flex-wrap:wrap}.card{background:white;border-left:4px solid #126d78;padding:16px;min-width:180px}strong{font-size:28px}.note{color:#496375}svg{width:100%;height:auto;max-height:420px}</style><main>",
            "<h1>BatchScope · Quality review / 质量复核</h1>", f"<p>As of / 截至：{escape(result['as_of'])} · {escape(result['version'])} · Synthetic / 模拟数据</p>",
            "<div class='cards'>"]
    from ui_text import tr
    for key, value in operations["metrics"].items():
        html.append(f"<div class='card'><strong>{value}</strong><br>{escape(tr(key,'en'))} / {escape(tr(key,'zh'))}</div>")
    html.append("</div><p class='note'>Due soon = outstanding, due in 1–7 days. Due today is not overdue. A closed parent with an outstanding action is a follow-up prompt, not proof of noncompliance. Age bands are illustrative; priority reflects time, not quality risk.<br>近期到期：未完成且 1–7 天内到期；今天到期不算逾期。偏差关闭但措施未完成仅提示复核，不证明违规。积压分段为示例，按时间显示不代表质量风险。</p>")
    monthly = operations["monthly"]
    if monthly:
        largest = max(r["ending_open"] for r in monthly) or 1
        html.append("<section><h2>Ending open backlog / 各期末未关闭偏差</h2><svg role='img' aria-label='Ending open deviations' viewBox='0 0 900 340'>")
        step = 830 / len(monthly)
        for index, row in enumerate(monthly):
            x, height = 45+index*step, row["ending_open"] / largest * 235
            html.append(f"<rect x='{x:.1f}' y='{265-height:.1f}' width='{step*.65:.1f}' height='{height:.1f}' fill='#126d78'/><text x='{x:.1f}' y='{255-height:.1f}' font-size='16'>{row['ending_open']}</text><text x='{x:.1f}' y='292' font-size='13'>{escape(row['period'][2:])}</text>")
        html.append("</svg><p>Final period ends on the analysis date, including partial months. Counts are not manufacturing-quality rates.<br>最后一期截至分析日期，可以是不完整月份；计数不等于生产质量异常率。</p></section>")
    for name, columns in schemas.items():
        html.append(f"<section><h2>{escape(tr('review_'+name,'en'))} / {escape(tr('review_'+name,'zh'))}</h2><div class='scroll'><table><thead><tr>")
        html.extend(f"<th>{escape(field_label(c))}</th>" for c in columns)
        html.append("</tr></thead><tbody>")
        for row in operations[name]:
            html.append("<tr>" + "".join(f"<td>{escape(display_value(c,row[c]))}</td>" for c in columns) + "</tr>")
        html.append("</tbody></table></div></section>")
    html.append("<section><h2>Input fingerprints / 输入指纹</h2><ul>")
    html.extend(f"<li>{escape(k)}: <code>{escape(v)}</code></li>" for k, v in result["input_sha256"].items())
    html.append("</ul></section><p class='note'>Synthetic portfolio prototype; no batch release, risk prediction, OOS conclusions, electronic signatures or validated GMP/CSV system. / 模拟作品集原型，不用于批次放行、风险预测、OOS 结论、电子签名或已验证 GMP/CSV 系统。</p></main></html>")
    (Path(output) / "QUALITY_REVIEW.html").write_text("\n".join(html), encoding="utf-8")
