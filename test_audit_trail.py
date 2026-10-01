import copy
from contextlib import closing
import csv
from pathlib import Path
import sqlite3
import tempfile
import tkinter as tk
import unittest

from audit_trail import FIELDS, POLICY, export_audit, generate_audit, review_audit


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.path=generate_audit(self.root/'events.csv')

    def write(self, rows):
        with self.path.open('w',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)

    def test_demo_rules_and_source_preserved(self):
        before=self.path.read_bytes();r=review_audit(self.path)
        self.assertEqual(r['counts'],{'reason.missing':2,'permission.mismatch':1,
                         'time.outside_hours':1,'timestamp.order':1,'timestamp.invalid':1})
        self.assertEqual(r['affected_events'],4)
        self.assertEqual(self.path.read_bytes(),before)

    def test_offsets_calendar_boundary_and_unknown_role(self):
        rows=review_audit(self.path)['events'][:1]
        row={k:rows[0][k] for k in FIELDS};row.update(action='update',reason='Correction')
        row['timestamp']='2026-06-29T10:00:00+02:00';self.write([row])
        self.assertFalse(review_audit(self.path)['findings'])
        row['timestamp']='2026-06-29T18:00:00Z';row['role']='unmapped';self.write([row])
        self.assertEqual(set(review_audit(self.path)['counts']),{'permission.unknown','time.outside_hours'})
        row['timestamp']='2026-06-29T10:00:00';self.write([row])
        self.assertIn('timestamp.invalid',review_audit(self.path)['counts'])

    def test_order_is_per_record_and_duplicate_ids_keep_row_identity(self):
        r=review_audit(self.path);rows=[{k:e[k] for k in FIELDS} for e in r['events'][:2]]
        rows[1].update(record_id='other',timestamp='2026-06-29T09:00:00Z',event_id='E001',reason='Correction')
        self.write(rows);r=review_audit(self.path)
        self.assertEqual(r['counts'],{'event.duplicate':1})
        self.assertEqual(r['findings'][0]['source_row'],3)

    def test_policy_changes_do_not_mutate_default(self):
        p=copy.deepcopy(POLICY);p['permissions']['admin'].append('delete')
        r=review_audit(self.path,p)
        self.assertNotIn('permission.mismatch',r['counts'])
        self.assertNotIn('delete',POLICY['permissions']['admin'])
        p['timezone']='local'
        with self.assertRaises(ValueError):review_audit(self.path,p)

    def test_export_join_html_escape_and_no_overwrite(self):
        r=review_audit(self.path);r['findings'][0]['explanation_en']='<script>alert(1)</script>'
        r['findings'][0]['event_id']='=1+1'
        out=export_audit(r,self.root/'report')
        self.assertIn('&lt;script&gt;', (out/'AUDIT.en.html').read_text(encoding='utf-8'))
        with closing(sqlite3.connect(out/'audit.sqlite')) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM findings f JOIN events e USING(source_row)').fetchone()[0],6)
        self.assertIn("'=1+1",(out/'findings.csv').read_text(encoding='utf-8-sig'))
        with self.assertRaises(FileExistsError):export_audit(r,out)

    def test_malformed_csv_fails_without_partial_review(self):
        self.path.write_text('bad,header\n1,2',encoding='utf-8')
        with self.assertRaises(ValueError):review_audit(self.path)

    def test_oversized_cell_gives_recoverable_error(self):
        row={key:'' for key in FIELDS};row['reason']='x'*(csv.field_size_limit()+1)
        self.write([row])
        with self.assertRaisesRegex(ValueError,'Cannot parse audit CSV'):
            review_audit(self.path)

    def test_desktop_demo_search_language_and_batch_link(self):
        from app import Window
        from quality_ops import analyse, generate
        generate(self.root/'inputs',batches=20)
        result=analyse(self.root/'inputs',self.root/'quality','2026-06-30')
        root=tk.Tk();root.withdraw()
        try:
            owner=Window(root);owner.result=result
            view=owner.open_audit();view.window.withdraw()
            path=generate_audit(self.root/'linked.csv',[result['operations']['batches'][0]['batch_id']])
            view.load(path)
            self.assertEqual(len(view.table.rows),6)
            view.search.set('demo-admin');self.assertEqual(len(view.table.rows),3)
            owner.toggle_language();self.assertEqual(view.title.cget('text'),'Audit log review')
            view.table.tree.selection_set('0')
            batch=view.batch();self.assertIsNotNone(batch)
            self.assertIs(view.snapshot,result)
        finally:
            root.destroy()


if __name__=='__main__':unittest.main()
