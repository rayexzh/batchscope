"""Portable lab progress, separate from completed experiment reports."""
import base64
import hashlib
import json
from pathlib import Path
import tempfile
from decimal_values import dumps
from qualitylab import Laboratory, EDITABLE
from quality_ops import iso_date


def save_session(path, model, state):
    iso_date(state['as_of'])
    payload = {'kind': 'batchscope-lab-progress', 'format': 1,
               'snapshot': base64.b64encode(model._snapshot_bytes).decode('ascii'),
               'sha256': model.source_sha256, 'source_as_of': model.as_of,
               'changes': model.changes, 'state': state}
    # Validate before writing; never replace an earlier saved copy.
    encoded = dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')
    if len(encoded) > 64 * 1024 * 1024:
        raise ValueError('Progress file is too large. / 进度文件过大。')
    with Path(path).open('xb') as handle:
        handle.write(encoded)


def load_session(path):
    if Path(path).stat().st_size > 64 * 1024 * 1024:
        raise ValueError('Progress file is too large. / 进度文件过大。')
    try:
        payload = json.loads(Path(path).read_text(encoding='utf-8'))
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
        iso_date(state['as_of'])
        if state['selected_id'] is not None and state['selected_id'] not in model._tests:
            raise ValueError('Unknown selected test')
        for test_id, form in state['forms'].items():
            if test_id not in model._tests or set(form) != {'main', 'repeat'}:
                raise ValueError('Invalid draft record')
            plan = form['repeat']
            if plan['rounds'] not in ('2', '3') or not isinstance(plan['reason'], str) or len(plan['fields']) != 2:
                raise ValueError('Invalid repeat plan')
            for fields in [form['main'], *plan['fields']]:
                if set(fields) != set(EDITABLE) or not all(isinstance(v, str) and len(v) <= 4096 for v in fields.values()):
                    raise ValueError('Invalid draft fields')
        # Re-evaluate recorded attempts; saved summaries are never trusted.
        for exercise in state['rechecks']:
            verified = model.recheck(exercise['test_id'], exercise['planned_rounds'], exercise['reason'])
            if json.loads(dumps(verified)) != exercise:
                raise ValueError('Saved attempt history differs from its plan')
        return model, state
    except (KeyError, TypeError, AttributeError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('Invalid lab progress file. / 进度文件格式不正确。') from exc
