"""Local review annotations; revision history is not a trusted audit trail."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

STATUSES = {
    'pending': ('未复核', 'Not reviewed'),
    'reviewing': ('正在复核', 'In review'),
    'follow_up': ('保留，需跟进', 'Retained for follow-up'),
    'explained': ('已说明，排除跟进', 'Explained; no follow-up'),
}


def context_id(result):
    payload={k:result[k] for k in ('sha256','ruleset','policy')}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()


class NoteStore:
    def __init__(self,path):
        self.path=Path(path)

    def connect(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        db=sqlite3.connect(self.path,timeout=5)
        db.execute('''CREATE TABLE IF NOT EXISTS revisions (
            context TEXT NOT NULL, source_row INTEGER NOT NULL, rule TEXT NOT NULL,
            revision INTEGER NOT NULL, status TEXT NOT NULL, reviewer TEXT NOT NULL,
            note TEXT NOT NULL, saved_at TEXT NOT NULL,
            PRIMARY KEY(context,source_row,rule,revision))''')
        db.commit()
        return db

    def history(self,result):
        if not self.path.exists():return []
        with closing(self.connect()) as db:
            cursor=db.execute('SELECT source_row,rule,revision,status,reviewer,note,saved_at FROM revisions WHERE context=? ORDER BY source_row,rule,revision',(context_id(result),))
            columns=[c[0] for c in cursor.description]
            return [dict(zip(columns,row)) for row in cursor]

    def latest(self,result):
        return {(r['source_row'],r['rule']):r for r in self.history(result)}

    def save(self,result,source_row,rule,status,reviewer,note,expected_revision=0):
        if (source_row,rule) not in {(f['source_row'],f['rule']) for f in result['findings']}:
            raise ValueError('Finding is not in this review / 检查项不属于当前复核。')
        reviewer,note=reviewer.strip(),note.strip()
        if status not in STATUSES:raise ValueError('Unknown review status / 未知状态。')
        if not reviewer or (status!='pending' and not note):
            raise ValueError('Enter reviewer name and an explanation / 请填写复核人，处理状态需填写理由。')
        if len(reviewer)>100 or len(note)>4000:raise ValueError('Name limit 100; note limit 4000 / 姓名最多 100 字，备注最多 4000 字。')
        record={'source_row':source_row,'rule':rule,'revision':expected_revision+1,
                'status':status,'reviewer':reviewer,'note':note,
                'saved_at':datetime.now(timezone.utc).isoformat()}
        with closing(self.connect()) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                current=db.execute('SELECT COALESCE(MAX(revision),0) FROM revisions WHERE context=? AND source_row=? AND rule=?',(context_id(result),source_row,rule)).fetchone()[0]
                if current!=expected_revision:
                    raise ValueError('Another window saved a newer revision. Reopen the finding before saving. / 另一窗口已保存新版本，请重新打开检查项后再保存。')
                db.execute('INSERT INTO revisions VALUES (?,?,?,?,?,?,?,?)',
                           (context_id(result),source_row,rule,record['revision'],status,reviewer,note,record['saved_at']))
                db.commit()
            except Exception:
                db.rollback();raise
        return record

    def bundle(self,result):
        history=self.history(result)
        latest={(r['source_row'],r['rule']):r for r in history}
        return {'context_id':context_id(result),'source_sha256':result['sha256'],
                'ruleset':result['ruleset'],'policy':result['policy'],
                'latest':list(latest.values()),'history':history,
                'scope':'Local reviewer-entered annotations; not authenticated signatures or tamper-proof history.'}
