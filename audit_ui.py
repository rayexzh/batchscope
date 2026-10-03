"""Bounded local audit demonstration, separate from manufacturing metrics."""
import json
import sqlite3
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from audit_trail import POLICY, export_audit, generate_audit, review_audit
from runtime_paths import output_root
from workbench_ui import BatchWindow
from audit_notes import NoteStore, STATUSES

TEXT = {
 'title': ('审计日志复核', 'Audit log review'),
 'generate': ('生成模拟日志', 'Generate sample log'),
 'open': ('打开日志 CSV', 'Open log CSV'),
 'export': ('导出完整报告', 'Export full report'),
 'batch': ('查看对应批次', 'Open linked batch'),
 'policy': ('选择规则 JSON', 'Choose policy JSON'),
 'timeline': ('多日期对比', 'Multi-date review'),
 'annotate': ('填写复核记录', 'Add review note'),
 'search': ('搜索事件、规则、用户或批次', 'Search events, rules, users or batches'),
 'scope': ('模拟日志；默认日历 UTC 周一至周五 08:00–18:00。待复核不等于违规。双击查看原始操作；批次关联使用打开窗口时的分析快照。',
           'Synthetic log; default calendar Mon–Fri 08:00–18:00 UTC. Flags are not violations. Double-click for source evidence; batch links use the snapshot captured when this window opened.'),
}


class AuditWindow:
    def __init__(self, owner, factory):
        self.owner, self.factory = owner, factory
        self.snapshot, self.result = owner.result, None
        self.policy, self.path = json.loads(json.dumps(POLICY)), None
        self.store=NoteStore(output_root()/'review-notes'/'audit-notes.sqlite')
        self.editors=[]
        self.window = tk.Toplevel(owner.root)
        self.window.protocol('WM_DELETE_WINDOW',self.close)
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
        note_row=ttk.Frame(frame);note_row.pack(fill='x',pady=4)
        self.filter=ttk.Combobox(note_row,state='readonly',width=25)
        self.filter.pack(side='left');self.filter.current() # values set during apply_view
        self.filter.bind('<<ComboboxSelected>>',lambda event:self.refresh())
        self.buttons['annotate']=ttk.Button(note_row,command=self.annotate)
        self.buttons['annotate'].pack(side='left',padx=8)
        panel = ttk.Frame(frame); panel.pack(fill='both',expand=True)
        self.table = factory(panel,owner,self.details)
        self.table.priority=['event_id','rule','review_status','batch_id','level','source_row','explanation','reviewer','review_note']
        self.scope = ttk.Label(frame,wraplength=800,style='Muted.TLabel'); self.scope.pack(fill='x',pady=8)
        self.search.trace_add('write',lambda *args:self.refresh())
        self.window.bind('<Configure>',lambda e:self.wrap(e) if e.widget==self.window else None)
        self.apply_view()

    def text(self,key):
        return TEXT[key][0 if self.owner.language=='zh' else 1]

    def confirm_close(self):
        return all(e.confirm_close() for e in self.editors if e.window.winfo_exists())

    def close(self):
        if self.confirm_close():self.window.destroy()

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
        index=max(0,self.filter.current())
        self.filter.configure(values=[('全部状态' if self.owner.language=='zh' else 'All statuses')]+[v[0 if self.owner.language=='zh' else 1] for v in STATUSES.values()])
        self.filter.current(index)
        self.refresh()
        self.editors=[e for e in self.editors if e.window.winfo_exists()]
        for editor in self.editors:editor.apply_view()

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
        except (ValueError,OSError,KeyError,sqlite3.Error) as exc:messagebox.showerror(self.text('title'),str(exc),parent=self.window)

    def open(self):
        path=filedialog.askopenfilename(parent=self.window,filetypes=[('CSV','*.csv')])
        if path:
            try:self.load(path)
            except (ValueError,OSError,UnicodeError,sqlite3.Error) as exc:messagebox.showerror(self.text('title'),str(exc),parent=self.window)

    def choose_policy(self):
        path=filedialog.askopenfilename(parent=self.window,filetypes=[('JSON','*.json')])
        if path:
            try:
                policy=json.loads(Path(path).read_text(encoding='utf-8-sig'))
                from audit_trail import validate_policy
                validate_policy(policy)
                if self.path:self.load(self.path,policy)
                else:self.policy=policy
            except (ValueError,OSError,KeyError,TypeError,sqlite3.Error) as exc:messagebox.showerror(self.text('title'),str(exc),parent=self.window)

    def refresh(self):
        rows=self.result['findings'] if self.result else []
        notes=self.store.latest(self.result) if self.result else {}
        rows=[{**r,'review_status':notes.get((r['source_row'],r['rule']),{}).get('status','pending'),
               'reviewer':notes.get((r['source_row'],r['rule']),{}).get('reviewer',''),
               'review_note':notes.get((r['source_row'],r['rule']),{}).get('note','')} for r in rows]
        status_code=(list(STATUSES)[self.filter.current()-1] if self.filter.current()>0 else None)
        needle=self.search.get().strip().casefold()
        events={e['source_row']:e for e in self.result['events']} if self.result else {}
        shown=[r for r in rows if (status_code is None or r['review_status']==status_code) and (not needle or needle in (' '.join(map(str,r.values()))+' '+ ' '.join(map(str,events[r['source_row']].values()))).casefold())]
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
        self.buttons['annotate'].configure(state='normal' if self.result else 'disabled')

    def annotate(self):
        row=self.table.selected()
        if not row:return None
        editor=NoteEditor(self,self.result,row)
        self.editors.append(editor)
        return editor

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
            export_audit(self.result,folder,self.store.bundle(self.result))
            messagebox.showinfo(self.text('export'),str(folder),parent=self.window)
        except (ValueError,OSError,sqlite3.Error) as exc:messagebox.showerror(self.text('title'),str(exc),parent=self.window)


class NoteEditor:
    def __init__(self,view,result,row):
        self.view,self.result,self.row=view,result,row
        current=view.store.latest(result).get((row['source_row'],row['rule']),{})
        self.revision=current.get('revision',0)
        self.window=tk.Toplevel(view.window);self.window.geometry('850x650');self.window.minsize(700,500)
        self.window.protocol('WM_DELETE_WINDOW',self.close)
        body=ttk.Frame(self.window);body.pack(fill='both',expand=True)
        self.canvas=tk.Canvas(body,highlightthickness=0)
        scrollbar=ttk.Scrollbar(body,orient='vertical',command=self.canvas.yview)
        scrollbar.pack(side='right',fill='y')
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side='left',fill='both',expand=True)
        frame=ttk.Frame(self.canvas,padding=16)
        content=self.canvas.create_window((0,0),window=frame,anchor='nw')
        frame.bind('<Configure>',lambda event:self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>',lambda event:self.canvas.itemconfigure(content,width=event.width))
        self.window.bind('<MouseWheel>',self.scroll,add='+')
        self.title=ttk.Label(frame,style='Title.TLabel');self.title.pack(anchor='w')
        ttk.Label(frame,text=f'{row["event_id"]} · {row["rule"]} · row {row["source_row"]}\nSHA-256: {result["sha256"]}',wraplength=790).pack(fill='x',pady=8)
        self.status=ttk.Combobox(frame,state='readonly');self.status.pack(fill='x',pady=5)
        self.status.current() # values set in apply_view
        self.status_code=current.get('status','pending')
        self.reviewer_label=ttk.Label(frame);self.reviewer_label.pack(anchor='w')
        self.reviewer=tk.StringVar(value=current.get('reviewer',''))
        ttk.Entry(frame,textvariable=self.reviewer).pack(fill='x',pady=4)
        self.note_label=ttk.Label(frame);self.note_label.pack(anchor='w')
        self.note=tk.Text(frame,height=6,wrap='word',font='TkDefaultFont');self.note.pack(fill='x',pady=5)
        self.note.insert('1.0',current.get('note',''))
        self.original=(self.status_code,self.reviewer.get().strip(),self.note.get('1.0','end').strip())
        self.history_text=tk.Text(frame,height=5,wrap='word',font='TkDefaultFont');self.history_text.pack(fill='both',expand=True,pady=5)
        footer=ttk.Frame(self.window,padding=(16,4,16,8));footer.pack(fill='x')
        self.save_button=ttk.Button(footer,command=self.save);self.save_button.pack(side='left',padx=(0,12))
        self.notice=ttk.Label(footer,wraplength=560);self.notice.pack(side='left',fill='x',expand=True)
        self.apply_view();self.status.current(list(STATUSES).index(self.status_code));self.show_history()

    def scroll(self,event):
        if event.delta and not isinstance(event.widget,tk.Text):
            self.canvas.yview_scroll(-1 if event.delta>0 else 1,'units')
            return 'break'

    def apply_view(self):
        zh=self.view.owner.language=='zh'
        self.window.title('BatchScope · '+('复核记录' if zh else 'Review note'))
        self.title.configure(text='复核记录' if zh else 'Review note')
        index=max(0,self.status.current())
        self.status.configure(values=[v[0 if zh else 1] for v in STATUSES.values()]);self.status.current(index)
        self.reviewer_label.configure(text='复核人（手动填写，非身份认证）' if zh else 'Reviewer (self-entered, not authenticated)')
        self.note_label.configure(text='备注或处理理由' if zh else 'Note or decision reason')
        self.save_button.configure(text='保存复核记录' if zh else 'Save review note')
        self.notice.configure(text='状态不改变原始检查结果；历史记录不是防篡改审计追踪。' if zh else 'Status does not change findings; local history is not tamper-proof.')
        self.canvas.configure(background=self.view.owner.colors['background'])
        self.note.configure(background=self.view.owner.colors['surface'],foreground=self.view.owner.colors['text'],insertbackground=self.view.owner.colors['text'])
        self.history_text.configure(background=self.view.owner.colors['surface'],foreground=self.view.owner.colors['text'])

    def show_history(self):
        rows=[r for r in self.view.store.history(self.result) if (r['source_row'],r['rule'])==(self.row['source_row'],self.row['rule'])]
        self.history_text.configure(state='normal');self.history_text.delete('1.0','end')
        self.history_text.insert('1.0','\n'.join(f'v{r["revision"]} · {r["saved_at"]} · {r["reviewer"]} · {r["status"]}\n{r["note"]}' for r in rows))
        self.history_text.configure(state='disabled')

    def save(self):
        try:
            record=self.view.store.save(self.result,self.row['source_row'],self.row['rule'],
                       list(STATUSES)[self.status.current()],self.reviewer.get(),self.note.get('1.0','end'),self.revision)
            self.revision=record['revision'];self.show_history();self.view.refresh()
            self.original=(record['status'],record['reviewer'],record['note'])
            self.notice.configure(text=('已保存 / Saved')+f' · v{self.revision}')
            return record
        except (ValueError,OSError,sqlite3.Error) as exc:
            self.notice.configure(text=str(exc));return None

    def confirm_close(self):
        current=(list(STATUSES)[self.status.current()],self.reviewer.get().strip(),self.note.get('1.0','end').strip())
        if current==self.original:return True
        choice=messagebox.askyesnocancel('BatchScope','Save this note before closing? / 关闭前保存这条备注？',parent=self.window)
        if choice is None:return False
        return bool(self.save()) if choice else True

    def close(self):
        if self.confirm_close():self.window.destroy()
