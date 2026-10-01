"""Read-only rule review of synthetic audit events; no compliance verdicts."""
import argparse
from collections import Counter
from contextlib import closing
import csv
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import sqlite3

FIELDS = 'event_id timestamp user_id role action record_type record_id batch_id old_value new_value reason'.split()
POLICY = {
    'timezone': 'UTC', 'work_start': 8, 'work_end': 18,
    'workdays': [0, 1, 2, 3, 4],
    'permissions': {'QC': ['create', 'update'], 'QA': ['create', 'update', 'delete'],
                    'admin': ['access_change']},
}
LABELS = {
    'reason.missing': ('Missing change reason', '缺少修改原因'),
    'permission.mismatch': ('Action outside configured role permissions', '操作不在配置角色权限内'),
    'permission.unknown': ('Role or action not covered by policy', '配置未覆盖此角色或操作'),
    'timestamp.invalid': ('Timestamp must include a UTC offset', '时间戳无效或缺少时区'),
    'timestamp.order': ('Time goes backwards in supplied record order', '同一记录的时间在输入顺序中倒退'),
    'time.outside_hours': ('Outside configured working hours', '工作时间外操作'),
    'event.duplicate': ('Repeated event identifier', '事件编号重复'),
    'event.incomplete': ('Required identity field is blank', '必需标识字段为空'),
}


def validate_policy(policy):
    if not isinstance(policy, dict) or not all(k in policy for k in POLICY):
        raise ValueError('Policy must contain timezone, work_start, work_end, workdays and permissions.')
    if policy.get('timezone') != 'UTC':
        raise ValueError('This prototype supports an explicit UTC working calendar only.')
    start, end = policy['work_start'], policy['work_end']
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= 24:
        raise ValueError('Working hours must be integers with 0 <= start < end <= 24.')
    if not isinstance(policy['workdays'], list) or not policy['workdays'] or any(type(x) is not int or not 0 <= x <= 6 for x in policy['workdays']):
        raise ValueError('Working days must be weekday numbers 0..6.')
    if not isinstance(policy['permissions'], dict) or any(
        not isinstance(v, list) or any(a not in ('create','update','delete','access_change') for a in v)
        for v in policy['permissions'].values()
    ):
        raise ValueError('Invalid permission configuration.')


def generate_audit(path, batch_ids=None):
    path = Path(path)
    if path.exists():
        raise ValueError('Choose a new file; existing logs are not overwritten.')
    batches = list(batch_ids or ['B0001', 'B0002'])
    if not batches:
        raise ValueError('At least one batch is needed.')
    rows = [
        ['E001','2026-06-29T10:00:00+00:00','demo-qc','QC','create','test_result','DEMO-T1',batches[0],'','99','Initial entry'],
        ['E002','2026-06-29T11:00:00+00:00','demo-qc','QC','update','test_result','DEMO-T1',batches[0],'99','98',''],
        ['E003','2026-06-29T23:00:00+00:00','demo-admin','admin','delete','test_result','DEMO-T1',batches[0],'98','',''],
        ['E004','2026-06-29T09:00:00+00:00','demo-qa','QA','update','test_result','DEMO-T1',batches[0],'98','97','Demonstration correction'],
        ['E005','not-a-date','demo-qa','QA','update','deviation','DEMO-D2',batches[-1],'open','closed','Reviewed'],
        ['E006','2026-06-30T10:00:00+00:00','demo-admin','admin','access_change','account','DEMO-U1',batches[-1],'QC','QA','Training role change'],
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.writer(handle); writer.writerow(FIELDS); writer.writerows(rows)
    return path


def review_audit(path, policy=None):
    policy = json.loads(json.dumps(POLICY if policy is None else policy))
    validate_policy(policy)
    # Read once: provenance and parsed records refer to the same source bytes.
    raw = Path(path).read_bytes()
    import io
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig'), newline=''))
    if reader.fieldnames != FIELDS:
        raise ValueError('Expected audit columns in the documented order: ' + ', '.join(FIELDS))
    try:
        input_rows = list(reader)
    except csv.Error as exc:
        raise ValueError('Cannot parse audit CSV: ' + str(exc)) from exc
    events, findings, seen, previous = [], [], set(), {}
    for row_number, row in enumerate(input_rows, 2):
        if None in row or None in row.values():
            raise ValueError(f'Incorrect number of cells at CSV record {row_number}.')
        event = {'source_row': row_number, **row}
        events.append(event)
        def flag(rule, level='review'):
            en, zh = LABELS[rule]
            findings.append({'source_row': row_number, 'event_id': row['event_id'],
                             'batch_id': row['batch_id'], 'rule': rule, 'level': level,
                             'explanation_en': en, 'explanation_zh': zh})
        if any(not row[k].strip() for k in ('event_id','user_id','role','action','record_type','record_id')):
            flag('event.incomplete', 'input')
        if row['event_id'] in seen:
            flag('event.duplicate', 'input')
        seen.add(row['event_id'])
        action, role = row['action'].strip(), row['role'].strip()
        if action in ('update', 'delete', 'access_change') and not row['reason'].strip():
            flag('reason.missing')
        if role not in policy['permissions'] or action not in ('create','update','delete','access_change'):
            flag('permission.unknown', 'input')
        elif action not in policy['permissions'][role]:
            flag('permission.mismatch')
        try:
            stamp = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
            if stamp.tzinfo is None:
                raise ValueError('Missing offset')
            stamp = stamp.astimezone(timezone.utc)
        except (ValueError, OverflowError):
            flag('timestamp.invalid', 'input')
            continue
        key = (row['record_type'], row['record_id'])
        if key in previous and stamp < previous[key]:
            flag('timestamp.order')
        previous[key] = max(stamp, previous.get(key, stamp))
        if action in ('update','delete','access_change') and (
            stamp.weekday() not in policy['workdays'] or not policy['work_start'] <= stamp.hour < policy['work_end']
        ):
            flag('time.outside_hours', 'context')
    return {'events': events, 'findings': findings, 'policy': policy,
            'source': str(Path(path).resolve()), 'sha256': hashlib.sha256(raw).hexdigest(),
            'ruleset': 'audit-review-0.1', 'reviewed_at': datetime.now(timezone.utc).isoformat(),
            'counts': dict(Counter(f['rule'] for f in findings)),
            'affected_events': len({f['source_row'] for f in findings})}


def export_audit(result, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    (folder/'audit-review.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    with closing(sqlite3.connect(folder/'audit.sqlite')) as db:
        for name, rows, columns in (
            ('events', result['events'], ['source_row']+FIELDS),
            ('findings', result['findings'], ['source_row','event_id','batch_id','rule','level','explanation_en','explanation_zh']),
        ):
            db.execute(f'CREATE TABLE {name} (' + ','.join(f'{c} '+('INTEGER' if c=='source_row' else 'TEXT') for c in columns)+')')
            db.executemany(f'INSERT INTO {name} VALUES ({",".join("?" for _ in columns)})',
                           [[r[c] for c in columns] for r in rows])
        db.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT)')
        db.executemany('INSERT INTO metadata VALUES (?,?)',
                       [(k, json.dumps(result[k], ensure_ascii=False)) for k in ('source','sha256','policy','ruleset','reviewed_at')])
        db.commit()
    from quality_ops import write_csv
    columns = ['source_row','event_id','batch_id','rule','level','explanation_en','explanation_zh']
    write_csv(folder/'findings.csv', columns, [[r[c] for c in columns] for r in result['findings']])
    for lang, index in [('en',0),('zh-CN',1)]:
        title = ['Audit log review', '审计日志复核'][index]
        scope = ['Synthetic prototype. Findings prompt review; they do not establish a regulatory violation. Input order is not a trusted event sequence. Working calendar: UTC.',
                 '模拟原型。检查结果用于复核，不构成法规违规结论。文件顺序不是可信事件顺序。工作日历：UTC。'][index]
        rows = ''.join('<tr>'+''.join('<td>'+html.escape(str(r[c]))+'</td>' for c in ['source_row','event_id','batch_id','rule','explanation_'+('en' if index==0 else 'zh')])+'</tr>' for r in result['findings'])
        body = f'<!doctype html><html lang="{lang}"><meta charset="utf-8"><title>{title}</title><style>body{{font:16px sans-serif;max-width:1100px;margin:32px auto;padding:16px}}td,th{{border:1px solid #bbb;padding:8px}}table{{border-collapse:collapse}}</style><h1>{title}</h1><p>{scope}</p><p>{len(result["events"])} events / 事件 · {result["affected_events"]} flagged / 待复核 · {len(result["findings"])} findings / 检查项</p><p>{html.escape(result["source"])}</p><p>SHA-256: {result["sha256"]}</p><pre>{html.escape(json.dumps(result["policy"],ensure_ascii=False,indent=2))}</pre><table><tr><th>Row / 行</th><th>Event / 事件</th><th>Batch / 批次</th><th>Rule / 规则</th><th>Finding / 说明</th></tr>{rows}</table></html>'
        (folder/f'AUDIT.{lang}.html').write_text(body,encoding='utf-8')
    (folder/'manifest.json').write_text(json.dumps({
        'complete': True, 'source_sha256': result['sha256'], 'ruleset': result['ruleset'],
        'artifacts': {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.iterdir()) if p.is_file()},
    },indent=2),encoding='utf-8')
    return folder


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv'); parser.add_argument('--output', required=True)
    parser.add_argument('--policy', help='Optional JSON policy; default UTC demonstration policy')
    args = parser.parse_args()
    policy = json.loads(Path(args.policy).read_text(encoding='utf-8')) if args.policy else None
    print(export_audit(review_audit(args.csv, policy), args.output))
