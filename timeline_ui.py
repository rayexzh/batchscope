"""Date-list review window with captured results, adjacent movements and a plot."""
from datetime import date
import json
from pathlib import Path
import queue
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from runtime_paths import output_root
from timeline import audit_timeline, export_timeline, quality_timeline, validate_dates


class TimelineWindow:
    def __init__(self,owner,factory,inputs=None,audit=None):
        self.owner,self.factory,self.inputs,self.audit=owner,factory,inputs,audit
        self.result,self.busy,self.output=None,False,None
        self.events=queue.Queue();self.poll_id=None
        self.window=tk.Toplevel(owner.root);self.window.geometry('1150x820');self.window.minsize(850,600)
        frame=ttk.Frame(self.window,padding=16);frame.pack(fill='both',expand=True)
        self.title=ttk.Label(frame,style='Title.TLabel');self.title.pack(anchor='w')
        self.hint=ttk.Label(frame,wraplength=1000);self.hint.pack(fill='x',pady=6)
        self.dates=tk.StringVar(value='2026-04-30, 2026-05-31, 2026-06-30, 2026-07-31')
        self.entry=ttk.Entry(frame,textvariable=self.dates);self.entry.pack(fill='x')
        row=ttk.Frame(frame);row.pack(fill='x',pady=8)
        self.run_button=ttk.Button(row,command=self.start);self.run_button.pack(side='left')
        self.export_button=ttk.Button(row,command=self.export,state='disabled');self.export_button.pack(side='left',padx=8)
        self.status=ttk.Label(frame,wraplength=1000);self.status.pack(fill='x',pady=6)
        self.canvas=tk.Canvas(frame,height=210,highlightthickness=0);self.canvas.pack(fill='x',pady=6)
        self.book=ttk.Notebook(frame);self.book.pack(fill='both',expand=True)
        keys=('rows','rules','unplaced') if audit is not None else ('rows','metrics','deviations','actions','measurements')
        self.tables={}
        for key in keys:
            panel=ttk.Frame(self.book);self.book.add(panel)
            table=factory(panel,owner,lambda k=key:self.details(k));table.tree.configure(height=6)
            table.priority=['date','from_date','to_date','metric','before_value','after_value','delta','change','batch_id']
            self.tables[key]=table
        self.window.bind('<Configure>',lambda event:self.draw() if event.widget==self.window else None)
        self.window.bind('<Destroy>',self.destroy,add='+')
        self.apply_view();self.poll_id=self.window.after(100,self.poll)

    def label(self,en,zh):return zh if self.owner.language=='zh' else en

    def apply_view(self):
        self.window.title('BatchScope · '+self.label('Multi-date review','多日期对比'))
        self.window.configure(background=self.owner.colors['background'])
        self.title.configure(text=self.label('Multi-date review','多日期对比'))
        self.hint.configure(text=self.label('Enter 2–12 distinct dates separated by commas. Dates are sorted; completed results keep their original date list.','输入 2–12 个不同日期，用逗号分隔。自动按日期排序；编辑后需重新运行，旧结果保留原日期。'))
        self.run_button.configure(text=self.label('Compare dates','运行多日期对比'))
        self.export_button.configure(text=self.label('Export full results','导出完整结果'))
        labels={'rows':('Date totals','各日期汇总'),'metrics':('Adjacent changes','相邻日期变化'),
                'deviations':('Deviation movements','偏差变化'),'actions':('Action movements','措施变化'),
                'measurements':('New measurements','新增检验'),'rules':('By rule','按规则统计'),'unplaced':('Unknown dates','无法归入日期')}
        for i,(key,table) in enumerate(self.tables.items()):
            self.book.tab(i,text=self.label(*labels[key]));table.populate(self.result.get(key,[]) if self.result else [])
        self.render_status();self.draw()

    def render_status(self,error=None):
        if error:self.status.configure(text=self.label('Failed: ','失败：')+error)
        elif self.busy:self.status.configure(text=self.label('Comparing…','正在对比…'))
        elif self.result:
            scope=(self.label('UTC event dates; undated events listed separately.','按 UTC 操作日期统计；无日期事件单列。') if self.audit is not None
                   else self.label('One input snapshot; changes compare adjacent endpoints.','同一输入快照；展示相邻日期端点变化。'))
            self.status.configure(text=', '.join(self.result['dates'])+'\n'+scope)
        else:self.status.configure(text=self.inputs or (self.audit['source'] if self.audit else '—'))

    def start(self):
        if self.busy:return
        try:
            dates=validate_dates([d.strip() for d in self.dates.get().replace('，',',').split(',')])
            if self.audit is None and (not self.inputs or not Path(self.inputs).is_dir()):
                raise ValueError('Choose the quality input folder first / 请先选择质量数据文件夹。')
        except ValueError as exc:
            self.render_status(str(exc));return
        self.busy=True;self.run_button.configure(state='disabled');self.export_button.configure(state='disabled')
        self.render_status()
        def worker():
            try:
                if self.audit is not None:
                    result=audit_timeline(self.audit,dates);output=None
                else:
                    root=output_root();root.mkdir(parents=True,exist_ok=True)
                    output=Path(tempfile.mkdtemp(prefix='timeline-',dir=root))/'results'
                    result=quality_timeline(self.inputs,dates,output)
                self.events.put((True,result,output))
            except Exception as exc:self.events.put((False,str(exc),None))
        threading.Thread(target=worker,daemon=True).start()

    def poll(self):
        try:ok,result,output=self.events.get_nowait()
        except queue.Empty:pass
        else:
            self.busy=False;self.run_button.configure(state='normal')
            if ok:self.result,self.output=result,output;self.apply_view()
            else:self.render_status(result)
            self.export_button.configure(state='normal' if self.result else 'disabled')
        self.poll_id=self.window.after(100,self.poll)

    def destroy(self,event):
        if event.widget==self.window and self.poll_id is not None:
            self.window.after_cancel(self.poll_id);self.poll_id=None

    def draw(self):
        self.canvas.delete('all');self.canvas.configure(background=self.owner.colors['surface'])
        if not self.result:return
        rows=self.result['rows'];w=max(700,self.canvas.winfo_width());h=210
        keys=('events','flagged_events') if self.audit is not None else ('open_deviations','overdue_actions')
        maximum=max(1,max(r[k] for r in rows for k in keys))
        days=[date.fromisoformat(r['date']).toordinal() for r in rows];span=max(1,days[-1]-days[0])
        self.canvas.create_line(65,45,65,175,w-30,175,fill=self.owner.colors['muted'])
        self.canvas.create_text(45,45,text=str(maximum),fill=self.owner.colors['text'])
        self.canvas.create_text(45,175,text='0',fill=self.owner.colors['text'])
        from review import field_label
        colors=('#63cbb9','#f1b36c') if self.owner.theme=='dark' else ('#126d78','#b45825')
        for j,(key,color) in enumerate(zip(keys,colors)):
            self.canvas.create_text(70+j*300,18,text=field_label(key,self.owner.language),anchor='w',fill=color)
            points=[(65+(w-100)*(d-days[0])/span,175-125*r[key]/maximum) for d,r in zip(days,rows)]
            self.canvas.create_line(*[v for point in points for v in point],fill=color,width=3)
            for x,y in points:self.canvas.create_oval(x-4,y-4,x+4,y+4,fill=color,outline=color)
        for i,(d,row) in enumerate(zip(days,rows)):
            if i in (0,len(rows)-1) or len(rows)<=6:
                self.canvas.create_text(65+(w-100)*(d-days[0])/span,193,text=row['date'][5:],fill=self.owner.colors['text'])

    def details(self,key):
        row=self.tables[key].selected()
        if not row:return
        win=tk.Toplevel(self.window);win.title('BatchScope');win.geometry('850x480')
        text=tk.Text(win,wrap='word',font='TkFixedFont');text.pack(fill='both',expand=True)
        text.insert('1.0',json.dumps(row,ensure_ascii=False,indent=2));text.configure(state='disabled')

    def export(self):
        if not self.result:return
        parent=filedialog.askdirectory(parent=self.window)
        if not parent:return
        try:
            folder=Path(tempfile.mkdtemp(prefix='timeline-export-',dir=parent))/'results'
            export_timeline(self.result,folder)
            messagebox.showinfo(self.label('Export','导出'),str(folder),parent=self.window)
        except (OSError,ValueError) as exc:messagebox.showerror('BatchScope',str(exc),parent=self.window)
