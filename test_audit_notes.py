import copy
from contextlib import closing
import csv
from pathlib import Path
import sqlite3
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from audit_notes import NoteStore
from audit_trail import export_audit,generate_audit,review_audit


class NoteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.path=generate_audit(self.root/'audit.csv')
        self.result=review_audit(self.path);self.store=NoteStore(self.root/'notes.sqlite')
        self.finding=self.result['findings'][0]

    def save(self,status='follow_up',note='Ask for correction evidence',revision=0):
        f=self.finding
        return self.store.save(self.result,f['source_row'],f['rule'],status,'Demo QA',note,revision)

    def test_persistence_and_revision_history_leave_log_and_findings_unchanged(self):
        before=self.path.read_bytes();original=copy.deepcopy(self.result)
        self.save();self.save('explained','Stock correction evidence reviewed',1)
        reopened=NoteStore(self.store.path)
        notes=reopened.latest(self.result)
        self.assertEqual(len(reopened.history(self.result)),2)
        self.assertEqual(notes[(self.finding['source_row'],self.finding['rule'])]['status'],'explained')
        self.assertEqual(self.path.read_bytes(),before);self.assertEqual(self.result,original)

    def test_source_policy_and_rule_versions_do_not_reuse_notes(self):
        self.save()
        for key in ('sha256','ruleset','policy'):
            different=copy.deepcopy(self.result)
            if key=='policy':different[key]['work_end']=20
            else:different[key]='different'
            self.assertEqual(self.store.latest(different),{})

    def test_concurrent_editor_cannot_overwrite_newer_revision(self):
        self.save()
        with self.assertRaisesRegex(ValueError,'newer revision'):
            self.save('explained','Stale editor decision',0)
        self.assertEqual(len(self.store.history(self.result)),1)

    def test_invalid_notes_and_unknown_finding_do_not_create_storage(self):
        with self.assertRaises(ValueError):self.save(note=' ')
        with self.assertRaises(ValueError):self.save(status='compliant')
        with self.assertRaises(ValueError):
            self.store.save(self.result,999,'not-a-rule','follow_up','QA','Reason')
        self.assertFalse(self.store.path.exists())

    def test_full_export_retains_findings_and_escapes_notes(self):
        self.save(note='=SUM(1,2) <script>example</script>')
        annotations=self.store.bundle(self.result)
        out=export_audit(self.result,self.root/'export',annotations)
        with closing(sqlite3.connect(out/'audit.sqlite')) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM findings').fetchone()[0],6)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM review_notes').fetchone()[0],1)
        self.assertIn('&lt;script&gt;', (out/'AUDIT.en.html').read_text(encoding='utf-8'))
        self.assertIn("'=SUM", (out/'review_notes.csv').read_text(encoding='utf-8-sig'))
        annotations['context_id']='wrong'
        with self.assertRaises(ValueError):export_audit(self.result,self.root/'mismatch',annotations)
        self.assertFalse((self.root/'mismatch').exists())

    def test_gui_save_filter_language_reopen_and_unsaved_close(self):
        from app import Window
        root=tk.Tk();root.withdraw()
        try:
            app=Window(root);view=app.open_audit();view.window.withdraw();view.store=self.store
            view.load(self.path);view.table.tree.selection_set('0')
            editor=view.annotate();editor.window.withdraw()
            editor.reviewer.set('Demo QA');editor.status.current(3)
            editor.note.insert('1.0','Correction explained with evidence')
            self.assertIsNotNone(editor.save())
            view.filter.current(1);view.refresh();self.assertEqual(len(view.table.rows),5)
            view.filter.current(4);view.refresh();self.assertEqual(len(view.table.rows),1)
            app.toggle_language();self.assertEqual(view.table.rows[0]['review_status'],'explained')
            editor.note.insert('end',' Additional question')
            with patch('audit_ui.messagebox.askyesnocancel',return_value=None):
                self.assertFalse(editor.confirm_close())
            with patch('audit_ui.messagebox.askyesnocancel',return_value=True):
                self.assertTrue(editor.confirm_close())
            self.assertEqual(len(self.store.history(self.result)),2)
            second=app.open_audit();second.window.withdraw();second.store=self.store;second.load(self.path)
            self.assertEqual(second.table.rows[0]['review_status'],'explained')
        finally:root.destroy()


if __name__=='__main__':unittest.main()
