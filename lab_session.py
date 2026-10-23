"""Portable lab progress, separate from completed experiment reports."""
import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile
from decimal_values import dumps
from qualitylab import Laboratory, EDITABLE
from quality_ops import iso_date


def save_session(path, model, state):
    validate_state(model, state)
    payload = {'kind': 'batchscope-lab-progress', 'format': 1,
               'snapshot': base64.b64encode(model._snapshot_bytes).decode('ascii'),
               'sha256': model.source_sha256, 'source_as_of': model.as_of,
               'changes': model.changes, 'state': state}
    # Validate before writing; never replace an earlier saved copy.
    encoded = dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')
    if len(encoded) > 64 * 1024 * 1024:
        raise ValueError('Progress file is too large. / 进度文件过大。')
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.batchscope-', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        # Publish complete bytes atomically, without replacing an existing file.
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_session(path):
    if Path(path).stat().st_size > 64 * 1024 * 1024:
        raise ValueError('Progress file is too large. / 进度文件过大。')
    try:
        payload = json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique_object, parse_constant=reject_constant)
        if payload['kind'] != 'batchscope-lab-progress' or payload['format'] != 1:
            raise ValueError('Unsupported progress format')
        content = base64.b64decode(payload['snapshot'], validate=True)
        if hashlib.sha256(content).hexdigest() != payload['sha256']:
            raise ValueError('Snapshot checksum does not match')
        with tempfile.TemporaryDirectory(prefix='BatchScope-progress-') as folder:
            database = Path(folder) / 'snapshot.sqlite'
            database.write_bytes(content)
            model = Laboratory(database, payload['source_as_of'], payload['sha256'])
        model.source = 'Saved lab progress'
        for test_id, patch in payload['changes'].items():
            model.stage(test_id, patch)
        state = payload['state']
        validate_state(model, state)
        return model, state
    except (KeyError, TypeError, AttributeError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError('Invalid lab progress file. / 进度文件格式不正确。') from exc


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field / 进度文件有重复字段。')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('Non-finite JSON number / 进度文件含无效数值。')


def validate_plan(plan):
    if (not isinstance(plan, dict) or set(plan) != {'rounds', 'reason', 'fields'}
            or plan['rounds'] not in ('2', '3') or not isinstance(plan['reason'], str)
            or len(plan['reason']) > 4096 or not isinstance(plan['fields'], list) or len(plan['fields']) != 2):
        raise ValueError('Invalid repeat plan / 复检计划格式错误。')


def matches_exercise(plan, exercise):
    validate_plan(plan)
    planned = [{k: v.strip() for k, v in fields.items()} for fields in plan['fields'][:int(plan['rounds'])-1]]
    return planned == exercise['planned_rounds'] and plan['reason'].strip() == exercise['reason']


def validate_state(model, state):
    try:
        iso_date(state['as_of'])
        if state['selected_id'] is not None and state['selected_id'] not in model._tests:
            raise ValueError('Unknown selected test')
        for test_id, form in state['forms'].items():
            if test_id not in model._tests or set(form) != {'main', 'repeat'}:
                raise ValueError('Invalid draft record')
            plan = form['repeat']
            validate_plan(plan)
            for fields in [form['main'], *plan['fields']]:
                if set(fields) != set(EDITABLE) or not all(isinstance(v, str) and len(v) <= 4096 for v in fields.values()):
                    raise ValueError('Invalid draft fields')
        # Re-evaluate recorded attempts; saved summaries are never trusted.
        for exercise in state['rechecks']:
            verified = model.recheck(exercise['test_id'], exercise['planned_rounds'], exercise['reason'])
            if json.loads(dumps(verified)) != json.loads(dumps(exercise)):
                raise ValueError('Saved attempt history differs from its plan')
        for test_id, plan in state.get('evaluated_plans', {}).items():
            validate_plan(plan)
            for fields in plan['fields']:
                if set(fields) != set(EDITABLE) or not all(isinstance(v, str) and len(v) <= 4096 for v in fields.values()):
                    raise ValueError('Invalid evaluated fields')
            latest = next((e for e in reversed(state['rechecks']) if e['test_id'] == test_id), None)
            if latest is None or not matches_exercise(plan, latest):
                raise ValueError('Evaluated plan differs from attempt history')
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('Invalid lab progress fields / 进度字段格式不正确。') from exc
