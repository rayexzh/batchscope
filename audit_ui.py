"""Bounded local audit demonstration, separate from manufacturing metrics."""
import json
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from audit_trail import POLICY, export_audit, generate_audit, review_audit
from runtime_paths import output_root
from workbench_ui import BatchWindow

TEXT = {
 'title': ('审计日志复核', 'Audit log review'),
 'generate': ('生成模拟日志', 'Generate sample log'),
 'open': ('打开日志 CSV', 'Open log CSV'),
 'export': ('导出完整报告', 'Export full report'),
 'batch': ('查看对应批次', 'Open linked batch'),
 'policy': ('选择规则 JSON', 'Choose policy JSON'),
 'timeline': ('多日期对比', 'Multi-date review'),
 'search': ('搜索事件、规则、用户或批次', 'Search events, rules, users or batches'),
 'scope': ('模拟日志；默认日历 UTC 周一至周五 08:00–18:00。待复核不等于违规。双击查看原始操作；批次关联使用打开窗口时的分析快照。',
           'Synthetic log; default calendar Mon–Fri 08:00–18:00 UTC. Flags are not violations. Double-click for source evidence; batch links use the snapshot captured when this window opened.'),
}


class AuditWindow:
    def __init__(self, owner, factory):
        self.owner, self.factory = owner, factory
        self.snapshot, self.result = owner.result, None
        self.policy, self.path = json.loads(json.dumps(POLICY)), None
        self.window = tk.Toplevel(owner.root)
        self.window.geometry('1100x700'); self.window.minsize(850,500)
        frame = ttk.Frame(self.window, padding=18); frame.pack(fill='both',expand=True)
        self.title = ttk.Label(frame,style='Title.TLabel'); self.title.pack(anchor='w')
        self.buttons = {}
        for keys in [('generate','open','policy'),('export','batch','timeline')]:
            row = ttk.Frame(frame); row.pack(fill='x',pady=6)
            for key in keys:
                button = ttk.Button(row,command=self.choose_policy if key=='policy' else getattr(self,key)); button.pack(side='left',padx=(0,8))
                self.buttons[key]=button
        self.caption = ttk.Label(frame,wraplength=800); self.caption.pack(fill='x',pady=8)
        self.search_label = ttk.Label(frame); self.search_label.pack(anchor='w')
        self.search = tk.StringVar(); ttk.Entry(frame,textvariable=self.search).pack(fill='x',pady=6)
        panel = ttk.Frame(frame); panel.pack(fill='both',expand=True)
        self.table = factory(panel,owner,self.details)
        self.table.priority=['event_id','rule','batch_id','level','source_row','explanation']
        self.scope = ttk.Label(frame,wraplength=800,style='Muted.TLabel'); self.scope.pack(fill='x',pady=8)
        self.search.trace_add('write',lambda *args:self.refresh())
        self.window.bind('<Configure>',lambda e:self.wrap(e) if e.widget==self.window else None)
        self.apply_view()

    def text(self,key):
        return TEXT[key][0 if self.owner.language=='zh' else 1]

    def wrap(self,event):
        self.scope.configure(wraplength=max(400,event.width-50))
        self.caption.configure(wraplength=max(400,event.width-50))

    def apply_view(self):
        self.window.title('BatchScope · '+self.text('title'))
        self.window.configure(background=self.owner.colors['background'])
        self.title.configure(text=self.text('title'))
        for key,button in self.buttons.items():button.configure(text=self.text(key))
        self.scope.configure(text=self.text('scope'))
        self.search_label.configure(text=self.text('search'))
        self.refresh()

    def load(self,path,policy=None):
        # Limit this first UI iteration; CLI supports larger logs without rendering every row.
        if Path(path).stat().st_size>5_000_000:
            raise ValueError('Desktop demo limit: 5 MB. Use audit_trail.py for larger files.')
        result=review_audit(path,self.policy if policy is None else policy)
        self.path,self.result=Path(path),result
        if policy is not None:self.policy=policy
        self.refresh()

    def generate(self):
        root=output_root();root.mkdir(parents=True,exist_ok=True)
        folder=Path(tempfile.mkdtemp(prefix='audit-demo-',dir=root))
        ids=[r['batch_id'] for r in self.snapshot['operations']['batches']] if self.snapshot else None
        try:self.load(generate_audit(folder/'audit_events.csv',ids))
        except (ValueError,OSError,KeyError) as exc:messagebox.showerror(self.text('title'),str(exc),parent=self.window)

    def open(self):
        path=filedialog.askopenfilename(parent=self.window,filetypes=[('CSV','*.csv')])
        if path:
            try:self.load(path)
            except (ValueError,OSError,UnicodeError) as exc:messagebox.showerror(self.text('title'),str(exc),parent=self.window)

    def choose_policy(self):
        path=filedialog.askopenfilename(parent=self.window,filetypes=[('JSON','*.json')])
        if path:
            try:
                policy=json.loads(Path(path).read_text(encoding='utf-8-sig'))
                from audit_trail import validate_policy
                validate_policy(policy)
                if self.path:self.load(self.path,policy)
                else:self.policy=policy
            except (ValueError,OSError,KeyError,TypeError) as exc:messagebox.showerror(self.text('title'),str(exc),parent=self.window)

    def refresh(self):
        rows=self.result['findings'] if self.result else []
        needle=self.search.get().strip().casefold()
        events={e['source_row']:e for e in self.result['events']} if self.result else {}
        shown=[r for r in rows if not needle or needle in (' '.join(map(str,r.values()))+' '+ ' '.join(map(str,events[r['source_row']].values()))).casefold()]
        language_key='explanation_zh' if self.owner.language=='zh' else 'explanation_en'
        display=[{**{k:v for k,v in r.items() if k not in ('explanation_zh','explanation_en')},'explanation':r[language_key]} for r in shown]
        self.table.populate(display)
        if self.result:
            counts=(f'{len(events)} 条事件 · {self.result["affected_events"]} 条待复核 · 显示 {len(shown)}/{len(rows)} 个检查项'
                    if self.owner.language=='zh' else f'{len(events)} events · {self.result["affected_events"]} flagged · {len(shown)}/{len(rows)} findings shown')
            self.caption.configure(text=f'{self.result["source"]}\n{counts}')
        else:self.caption.configure(text='—')
        self.buttons['export'].configure(state='normal' if self.result else 'disabled')
        self.buttons['batch'].configure(state='normal' if self.snapshot and self.result else 'disabled')
        self.buttons['timeline'].configure(state='normal' if self.result else 'disabled')

    def timeline(self):
        if not self.result:return None
        from timeline_ui import TimelineWindow
        view=TimelineWindow(self.owner,self.factory,audit=self.result)
        self.owner.review_views.append(view)
        return view

    def details(self):
        row=self.table.selected()
        if not row:return
        event=next(e for e in self.result['events'] if e['source_row']==row['source_row'])
        win=tk.Toplevel(self.window);win.title(self.text('title'));win.geometry('850x500')
        text=tk.Text(win,wrap='word',font='TkFixedFont');text.pack(fill='both',expand=True)
        text.insert('1.0',json.dumps({'event':event,'findings':[f for f in self.result['findings'] if f['source_row']==row['source_row']],'policy':self.result['policy']},ensure_ascii=False,indent=2));text.configure(state='disabled')

    def batch(self):
        row=self.table.selected()
        if not row or not self.snapshot:return
        ids={r['batch_id'] for r in self.snapshot['operations']['batches']}
        if row['batch_id'] not in ids:
            messagebox.showinfo(self.text('title'),'Batch not found in captured snapshot / 当前快照没有此批次',parent=self.window);return
        view=BatchWindow(self.owner,self.snapshot,row['batch_id'],self.factory)
        self.owner.review_views.append(view);return view

    def export(self):
        if not self.result:return
        parent=filedialog.askdirectory(parent=self.window)
        if not parent:return
        try:
            folder=Path(tempfile.mkdtemp(prefix='audit-report-',dir=parent))/'results'
            export_audit(self.result,folder)
            messagebox.showinfo(self.text('export'),str(folder),parent=self.window)
        except (ValueError,OSError) as exc:messagebox.showerror(self.text('title'),str(exc),parent=self.window)
