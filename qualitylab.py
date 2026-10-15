"""Isolated what-if experiments on a completed synthetic quality snapshot."""
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import html
import json
import math
from pathlib import Path
import sqlite3
import tempfile

from comparison import snapshot
from quality_ops import COLUMNS, ROOT, VERSION, iso_date, write_csv

EDITABLE = ('value', 'spec_low', 'spec_high', 'measured_on')
SCOPE = ('Synthetic what-if experiment only. Both arms use the same as-of date. '
         'Changed specifications are hypothetical, never approved limits. '
         'No source overwrite, batch release, or causal/business-impact claim.')
SCOPE_ZH = '仅模拟假设实验；两种情景使用同一截至日期。修改后的规格仅是假设，不是获批限度；不覆盖原始数据，不用于批次放行或推断实际业务效果。'


class Laboratory:
    """Capture once; later source-file or main-window changes cannot alter this lab."""
    def __init__(self, database, as_of, expected_sha256):
        iso_date(as_of)
        self.as_of = as_of
        self.source = str(Path(database).resolve())
        content = Path(database).read_bytes()
        self.source_sha256 = hashlib.sha256(content).hexdigest()
        if not expected_sha256 or self.source_sha256 != expected_sha256:
            raise ValueError('Snapshot database differs from its completed analysis. / 快照数据库与已完成分析不符。')
        # Parse the exact byte snapshot that was hashed, without depending on WAL
        # state or files that may be edited after this window opens.
        with tempfile.TemporaryDirectory(prefix='BatchScope-lab-read-') as folder:
            path = Path(folder) / 'snapshot.sqlite'
            path.write_bytes(content)
            with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
                self._data = {table: [dict(zip(columns, row)) for row in db.execute(
                    'SELECT ' + ','.join(columns) + ' FROM ' + table + ' ORDER BY ' + columns[0])]
                    for table, columns in COLUMNS.items()}
        self._tests = {row['test_id']: row for row in self._data['test_results']}
        self._made = {row['batch_id']: row['manufactured_on'] for row in self._data['batches']}
        self._products = {row['batch_id']: row['product'] for row in self._data['batches']}
        self.changes = {}
        self.revision = 0

    @property
    def tests(self):
        return [{**row, 'product': self._products[row['batch_id']]} for row in deepcopy(list(self._tests.values()))]

    def current(self, test_id):
        if test_id not in self._tests:
            raise ValueError('Unknown test ID / 未知检验编号。')
        return {**self._tests[test_id], **self.changes.get(test_id, {})}

    def stage(self, test_id, values):
        """Validate a whole record before replacing its queued edits."""
        row = self.current(test_id)
        if not isinstance(values, dict) or set(values) - set(EDITABLE):
            raise ValueError('Only result, bounds and measurement date may change. / 只能修改检验值、上下限与检验日期。')
        for key, value in values.items():
            if key == 'measured_on':
                iso_date(value)
                if value < self._made[row['batch_id']]:
                    raise ValueError('Measurement predates manufacture. / 检验日期不能早于生产日期。')
            else:
                if key == 'value' and (value is None or isinstance(value, str) and not value.strip()):
                    value = None
                else:
                    if isinstance(value, bool):
                        raise ValueError('Use a finite number / 请输入有限数值。')
                    try:
                        value = float(value)
                    except (TypeError, ValueError) as exc:
                        raise ValueError('Use a finite number / 请输入有限数值。') from exc
                    if not math.isfinite(value):
                        raise ValueError('Use a finite number / 请输入有限数值。')
            row[key] = value
        if row['spec_low'] > row['spec_high']:
            raise ValueError('Lower bound exceeds upper bound. / 下限不能高于上限。')
        patch = {key: row[key] for key in EDITABLE if row[key] != self._tests[test_id][key]}
        if patch:
            self.changes[test_id] = patch
        else:
            self.changes.pop(test_id, None)
        self.revision += 1

    def reset(self, test_id=None):
        if test_id is None:
            self.changes.clear()
        else:
            self.changes.pop(test_id, None)
        self.revision += 1

    def run(self, as_of):
        """Reuse production SQL in a disposable in-memory database for both arms."""
        iso_date(as_of)
        changes = deepcopy(self.changes)
        with closing(sqlite3.connect(':memory:')) as db:
            db.executescript((ROOT / 'schema.sql').read_text(encoding='utf-8'))
            for table, columns in COLUMNS.items():
                db.executemany('INSERT INTO ' + table + ' VALUES (' + ','.join('?' for _ in columns) + ')',
                               [[row[c] for c in columns] for row in self._data[table]])
            before = snapshot(db, as_of)
            for test_id, patch in changes.items():
                db.execute('UPDATE test_results SET ' + ','.join(key + '=?' for key in patch) + ' WHERE test_id=?',
                           [*patch.values(), test_id])
            after = snapshot(db, as_of)
        metrics = [{'metric': key, 'baseline_count': value, 'scenario_count': after['metrics'][key],
                    'delta': after['metrics'][key] - value} for key, value in before['metrics'].items()]
        before_rows = {row['test_id']: row for row in before['details']['01_test_ranges']}
        after_rows = {row['test_id']: row for row in after['details']['01_test_ranges']}
        transitions = []
        for test_id in changes:
            original = self._tests[test_id]
            changed = {**original, **changes[test_id]}
            transitions.append({
                'test_id': test_id, 'batch_id': original['batch_id'], 'product': self._products[original['batch_id']],
                'before_status': before_rows.get(test_id, {}).get('snapshot_status', 'not_measured'),
                'after_status': after_rows.get(test_id, {}).get('snapshot_status', 'not_measured'),
                'baseline_value': original['value'], 'scenario_value': changed['value'],
                'baseline_low': original['spec_low'], 'scenario_low': changed['spec_low'],
                'baseline_high': original['spec_high'], 'scenario_high': changed['spec_high'],
                'baseline_date': original['measured_on'], 'scenario_date': changed['measured_on'],
                'unit': original['unit'],
            })
        return {'kind': 'synthetic-quality-laboratory', 'version': VERSION,
                'source': self.source, 'source_sha256': self.source_sha256, 'source_as_of': self.as_of,
                'as_of': as_of, 'revision': self.revision, 'changes': changes,
                'metrics': metrics, 'transitions': transitions,
                'baseline_metrics': before['metrics'], 'scenario_metrics': after['metrics'],
                'created_at_utc': datetime.now(timezone.utc).isoformat(), 'scope': SCOPE, 'scope_zh': SCOPE_ZH}

    def recheck(self, test_id, rounds, reason):
        """A planned 2/3-attempt teaching exercise, never a replacement result."""
        if test_id not in self._tests or not isinstance(rounds, list) or not 1 <= len(rounds) <= 2:
            raise ValueError('Choose a test and one or two additional attempts. / 请选择记录及一至两次附加检验。')
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
            raise ValueError('Enter an exercise reason (1–2000 characters). / 请填写练习理由（1–2000 字）。')
        original = deepcopy(self._tests[test_id])
        attempts = []
        previous = original
        # Original result always remains attempt 1, even when later attempts
        # are within range. No mean or majority-vote acceptance is calculated.
        for index, supplied in enumerate([original, *rounds], 1):
            if index > 1:
                if not isinstance(supplied, dict) or set(supplied) != set(EDITABLE):
                    raise ValueError('Each planned attempt needs value, bounds and date. / 每轮需填写检验值、上下限及日期。')
                temporary = Laboratory.__new__(Laboratory)
                temporary.__dict__ = {**self.__dict__, 'changes': {}}
                temporary.stage(test_id, supplied)
                row = temporary.current(test_id)
                if row['measured_on'] < previous['measured_on']:
                    raise ValueError('Attempt dates must be chronological. / 检验轮次日期不能倒退。')
                if row['spec_low'] < previous['spec_low'] or row['spec_high'] > previous['spec_high']:
                    raise ValueError('Teaching ranges may stay equal or narrow, never widen. / 练习范围可保持或收窄，不能放宽。')
            else:
                row = original
            status = ('missing' if row['value'] is None else 'outside_range'
                      if row['value'] < row['spec_low'] or row['value'] > row['spec_high'] else 'within_range')
            attempts.append({'attempt': index, 'test_id': test_id, 'value': row['value'],
                             'spec_low': row['spec_low'], 'spec_high': row['spec_high'],
                             'measured_on': row['measured_on'], 'unit': original['unit'], 'snapshot_status': status})
            previous = row
        return {'kind': 'synthetic-recheck-exercise', 'test_id': test_id, 'reason': reason.strip(),
                'source_sha256': self.source_sha256, 'planned_rounds': deepcopy(rounds), 'attempts': attempts,
                'any_outside_range': any(row['snapshot_status'] == 'outside_range' for row in attempts),
                'original_status': attempts[0]['snapshot_status'],
                'note': 'All attempts retained. Repetition or narrower limits do not establish accuracy. This is not an OOS investigation or a retesting protocol.'}

    def export(self, result, destination):
        """Export a frozen experiment plus replayable inputs; completion is last."""
        if (result.get('kind') != 'synthetic-quality-laboratory'
                or result.get('source_sha256') != self.source_sha256):
            raise ValueError('Experiment belongs to another snapshot. / 实验不属于当前快照。')
        # Recalculate with the recorded settings, not the current edit queue.
        replay = Laboratory.__new__(Laboratory)
        replay.__dict__ = {**self.__dict__, 'changes': {}}
        for test_id, patch in result['changes'].items():
            replay.stage(test_id, patch)
        verified = replay.run(result['as_of'])
        for key in ('metrics', 'transitions', 'baseline_metrics', 'scenario_metrics'):
            if result[key] != verified[key]:
                raise ValueError('Experiment result does not match its recorded changes. / 实验结果与修改记录不符。')
        for exercise in result.get('rechecks', []):
            if exercise != self.recheck(exercise['test_id'], exercise['planned_rounds'], exercise['reason']):
                raise ValueError('Recheck exercise differs from its recorded plan. / 重复检验练习与所记录计划不符。')
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=False)
        (destination / 'EXPERIMENT.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        for name in ('metrics', 'transitions'):
            rows = result[name]
            columns = list(rows[0]) if rows else ['test_id', 'before_status', 'after_status']
            write_csv(destination / (name + '.csv'), columns, [[row[c] for c in columns] for row in rows])
        attempts = [row for exercise in result.get('rechecks', []) for row in exercise['attempts']]
        if attempts:
            write_csv(destination / 'recheck_attempts.csv', list(attempts[0]), [[row[c] for c in attempts[0]] for row in attempts])
        for arm in ('baseline', 'scenario'):
            folder = destination / arm
            folder.mkdir()
            for table, columns in COLUMNS.items():
                rows = deepcopy(self._data[table])
                if arm == 'scenario' and table == 'test_results':
                    rows = [{**row, **result['changes'].get(row['test_id'], {})} for row in rows]
                write_csv(folder / (table + '.csv'), columns, [[row[c] for c in columns] for row in rows])
            (folder / 'SOURCE.json').write_text(json.dumps({
                'data_type': 'synthetic', 'origin': 'BatchScope quality laboratory', 'arm': arm,
                'baseline_database_sha256': self.source_sha256, 'note': SCOPE}, indent=2), encoding='utf-8')
        for language, scope in (('en', SCOPE), ('zh-CN', SCOPE_ZH)):
            from review import field_label, display_value
            lang = 'zh' if language == 'zh-CN' else 'en'
            title = '质量数据实验室' if lang == 'zh' else 'Quality data laboratory'
            body = f'<!doctype html><html lang="{language}"><meta charset="utf-8"><title>{title}</title><style>body{{font:16px system-ui;max-width:1100px;margin:32px auto;padding:16px;background:#f3f7f5;color:#173c34}}table{{border-collapse:collapse;background:white;width:100%;margin:16px 0}}td,th{{border:1px solid #cad8d3;padding:8px;text-align:left}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}.scroll{{overflow:auto}}</style><h1>{title}</h1><p>{scope}</p><p>{html.escape(result["as_of"])}</p><p>SHA-256: {self.source_sha256}</p>'
            for name in ('metrics', 'transitions'):
                rows = result[name]
                if not rows:
                    body += '<p>' + ('没有修改记录。' if lang == 'zh' else 'No edited records.') + '</p>'
                    continue
                columns = list(rows[0])
                body += '<div class="scroll"><table><tr>' + ''.join('<th>' + html.escape(field_label(c, lang)) + '</th>' for c in columns) + '</tr>'
                body += ''.join('<tr>' + ''.join('<td>' + html.escape(display_value(c, row[c], lang)) + '</td>' for c in columns) + '</tr>' for row in rows) + '</table></div>'
            body += '<h2>' + ('实际修改字段' if lang == 'zh' else 'Recorded field changes') + '</h2><pre>' + html.escape(json.dumps(result['changes'], ensure_ascii=False, indent=2)) + '</pre></html>'
            if result.get('rechecks'):
                title = '重复检验练习：保留每次结果，不作放行判断' if lang == 'zh' else 'Recheck exercise: all attempts retained; no release verdict'
                detail = html.escape(json.dumps(result['rechecks'], ensure_ascii=False, indent=2))
                body = body.replace('</html>', '<h2>' + title + '</h2><pre>' + detail + '</pre></html>')
            (destination / ('LAB.' + language + '.html')).write_text(body, encoding='utf-8')
        artifacts = {p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(destination.rglob('*')) if p.is_file()}
        (destination / 'manifest.json').write_text(json.dumps({
            'complete': True, 'kind': result['kind'], 'source_sha256': self.source_sha256,
            'as_of': result['as_of'], 'artifacts': artifacts}, indent=2), encoding='utf-8')
        return destination
