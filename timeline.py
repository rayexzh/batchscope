"""Multi-date quality snapshots and audit-event timelines from fixed inputs."""
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from html import escape
import hashlib
import json
from pathlib import Path
import sqlite3

from comparison import snapshot, build_comparison
from quality_ops import analyse, iso_date, write_csv


def validate_dates(dates):
    if not 2 <= len(dates) <= 12:
        raise ValueError('Choose 2–12 dates / 请选择 2–12 个日期。')
    for day in dates:
        iso_date(day)
    if len(set(dates)) != len(dates):
        raise ValueError('Dates must be unique / 日期不能重复。')
    return sorted(dates)


def quality_timeline(inputs, dates, output):
    dates = validate_dates(dates)
    output = Path(output)
    if output.exists():
        raise ValueError('Choose a new output folder / 请选择新的输出目录。')
    # Validation/import is done once, with the latest endpoint. All dates use that DB.
    end = analyse(inputs, output/'end_snapshot', dates[-1])
    uri = (output/'end_snapshot/quality.sqlite').resolve().as_uri()+'?mode=ro'
    with closing(sqlite3.connect(uri, uri=True)) as db:
        snapshots = [snapshot(db, day) for day in dates]
        intervals = [build_comparison(db, a, b) for a,b in zip(snapshots, snapshots[1:])]
    rows = [{'date': s['as_of'], **s['metrics']} for s in snapshots]
    movements = {key: [{ 'from_date': interval['from_date'], 'to_date': interval['to_date'], **row}
                      for interval in intervals for row in interval[key]]
                 for key in ('metrics','deviations','actions','measurements')}
    result = {'kind': 'quality', 'dates': dates, 'rows': rows, **movements,
              'source': str(Path(inputs).resolve()), 'input_sha256': end['input_sha256'],
              'scope': 'One input snapshot; endpoint states and adjacent-date movements, not edit history or every interim episode.',
              'scope_zh': '同一份输入快照；各日期状态与相邻日期变化，不是编辑历史，也不涵盖期间所有短暂状态。'}
    export_timeline(result, output/'timeline')
    # Parent completion record only after all reports are written.
    result['artifact_sha256'] = {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in sorted(output.rglob('*')) if p.is_file()}
    (output/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


def audit_timeline(review, dates):
    dates = validate_dates(dates)
    dated, unplaced = {}, []
    for event in review['events']:
        try:
            stamp=datetime.fromisoformat(event['timestamp'].replace('Z','+00:00'))
            if stamp.tzinfo is None:raise ValueError('No offset')
            day=stamp.astimezone(timezone.utc).date().isoformat()
        except (ValueError,OverflowError):
            unplaced.append(event);continue
        dated[event['source_row']]=day
    flagged={f['source_row'] for f in review['findings']}
    rows, by_rule = [], []
    previous=None
    for day in dates:
        keys={key for key,date in dated.items() if date <= day}
        interval_keys={key for key in keys if previous is None or dated[key]>previous}
        findings=[f for f in review['findings'] if f['source_row'] in keys]
        rows.append({'date':day,'events':len(keys),'flagged_events':len(keys & flagged),
                     'findings':len(findings),'period_events':len(interval_keys),
                     'period_flagged_events':len(interval_keys & flagged)})
        for rule,count in sorted(Counter(f['rule'] for f in findings).items()):
            by_rule.append({'date':day,'rule':rule,'findings':count})
        previous=day
    return {'kind':'audit','dates':dates,'rows':rows,'rules':by_rule,'unplaced':unplaced,
            'source':review['source'],'sha256':review['sha256'],'policy':review['policy'],
            'ruleset':review['ruleset'],
            'scope':'UTC end-of-day event counts from the loaded full-log review; not historical reviewer status. First period includes all dated events through the first date. Invalid timestamps stay unplaced.',
            'scope_zh':'按 UTC 日终统计已加载完整日志中的事件；不是历史复核状态。首期包含截至首日的全部有日期事件，无效时间戳单列。'}


def export_timeline(result, folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    (folder/'TIMELINE.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    for key in ('rows','metrics','deviations','actions','measurements','rules','unplaced'):
        rows=result.get(key,[])
        if rows:
            columns=list(rows[0]);write_csv(folder/f'timeline_{key}.csv',columns,[[r[c] for c in columns] for r in rows])
    from review import field_label, display_value
    for language,code in [('en','en'),('zh','zh-CN')]:
        tables=[]
        for key in ('rows','metrics','rules','unplaced'):
            rows=result.get(key,[])
            if not rows:continue
            columns=list(rows[0])
            head=''.join('<th>'+escape(field_label(c,language))+'</th>' for c in columns)
            body=''.join('<tr>'+''.join('<td>'+escape(display_value(c,r[c],language))+'</td>' for c in columns)+'</tr>' for r in rows)
            tables.append(f'<h2>{escape(key)}</h2><div class="scroll"><table><tr>{head}</tr>{body}</table></div>')
        title='Multi-date review' if language=='en' else '多日期对比'
        scope=result['scope'] if language=='en' else result['scope_zh']
        (folder/f'TIMELINE.{code}.html').write_text(
            f'<!doctype html><html lang="{code}"><meta charset="utf-8"><title>{title}</title><style>body{{font:16px sans-serif;margin:32px;color:#18313e}}table{{border-collapse:collapse}}td,th{{padding:8px;border:1px solid #bbc}}.scroll{{overflow:auto}}</style><h1>BatchScope · {title}</h1><p>{escape(scope)}</p><p>{escape(result["source"])}</p><p>Synthetic demonstration / 模拟演示</p>'+''.join(tables),encoding='utf-8')
    (folder/'manifest.json').write_text(json.dumps({'complete':True,'artifacts':{
        p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.iterdir()) if p.is_file()}},indent=2),encoding='utf-8')
    return folder
