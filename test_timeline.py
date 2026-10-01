from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch

from audit_trail import generate_audit,review_audit
from quality_ops import analyse,generate
from timeline import audit_timeline,export_timeline,quality_timeline,validate_dates


class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.inputs=self.root/'inputs'
        generate(self.inputs)
        self.dates=['2026-05-31','2026-06-30','2026-07-31']

    def test_quality_endpoints_and_adjacent_movements_reconcile(self):
        result=quality_timeline(self.inputs,self.dates,self.root/'timeline')
        for row in result['rows']:
            independent=analyse(self.inputs,self.root/row['date'],row['date'])
            self.assertEqual({k:v for k,v in row.items() if k!='date'},independent['metrics'])
        for first,last in zip(result['rows'],result['rows'][1:]):
            actions=[r for r in result['actions'] if r['from_date']==first['date']]
            change=sum(r['change']=='newly_overdue' for r in actions)-sum(r['change']=='resolved_overdue' for r in actions)
            self.assertEqual(first['overdue_actions']+change,last['overdue_actions'])
        self.assertEqual([r['open_deviations'] for r in result['rows'][-2:]],[22,17])
        self.assertTrue((self.root/'timeline/manifest.json').exists())

    def test_inputs_loaded_once_and_invalid_dates_do_not_create_output(self):
        import quality_ops
        with patch('quality_ops.load_inputs',wraps=quality_ops.load_inputs) as load:
            quality_timeline(self.inputs,self.dates,self.root/'timeline')
            self.assertEqual(load.call_count,1)
        for dates in [[],['2026-06-30'],['2026-06-30']*2,['2026-02-30','2026-06-30'],[f'2026-01-{i:02d}' for i in range(1,14)]]:
            with self.assertRaises(ValueError):quality_timeline(self.inputs,dates,self.root/'invalid')
            self.assertFalse((self.root/'invalid').exists())
        self.assertEqual(validate_dates(self.dates[::-1]),self.dates)

    def test_audit_invalid_dates_are_separate_and_duplicate_findings_not_double_counted(self):
        path=generate_audit(self.root/'events.csv');review=review_audit(path)
        result=audit_timeline(review,['2026-06-28','2026-06-29','2026-06-30'])
        self.assertEqual([(r['events'],r['flagged_events'],r['findings']) for r in result['rows']],[(0,0,0),(4,3,5),(5,3,5)])
        self.assertEqual([r['period_events'] for r in result['rows']],[0,4,1])
        self.assertEqual([e['event_id'] for e in result['unplaced']],['E005'])
        path.unlink() # timeline uses captured evidence, not a later file read
        self.assertEqual(audit_timeline(review,result['dates'])['rows'],result['rows'])
        export_audit=export_timeline(result,self.root/'audit-report')
        self.assertTrue((export_audit/'timeline_unplaced.csv').exists())

    def test_audit_utc_date_cutoff(self):
        review=review_audit(generate_audit(self.root/'events.csv'))
        review['events'][0]['timestamp']='2026-06-30T00:30:00+02:00'
        result=audit_timeline(review,['2026-06-29','2026-06-30'])
        self.assertEqual(result['rows'][0]['events'],4)

    def test_desktop_date_edit_keeps_result_and_recovers_from_failure(self):
        from app import Window
        root=tk.Tk();root.withdraw()
        try:
            app=Window(root);app.inputs.set(str(self.inputs))
            view=app.open_timeline();view.window.withdraw();view.dates.set(','.join(self.dates));view.start()
            deadline=time.monotonic()+15
            while view.busy and time.monotonic()<deadline:root.update();time.sleep(.02)
            self.assertFalse(view.busy);self.assertIsNotNone(view.result)
            original=view.result
            view.dates.set('2026-02-30,2026-03-31');view.start()
            self.assertIs(view.result,original);self.assertIn('失败',view.status.cget('text'))
            view.dates.set('2026-06-30,2026-07-31');view.start()
            while view.busy and time.monotonic()<deadline:root.update();time.sleep(.02)
            self.assertEqual(view.result['dates'],['2026-06-30','2026-07-31'])
            app.toggle_language();self.assertEqual(view.title.cget('text'),'Multi-date review')
        finally:root.destroy()


if __name__=='__main__':unittest.main()
