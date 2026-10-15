"""Read-only input checks with row-level findings before starting analysis."""
from copy import deepcopy
import hashlib
import html
import json
from pathlib import Path
import queue
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from quality_ops import check_inputs, input_report, write_input_report, INPUT_FINDING_COLUMNS

TEXT = {
    'title': ('检查输入数据', 'Check input data'),
    'browse': ('选择数据文件夹', 'Choose input folder'),
    'check': ('开始检查', 'Check files'),
    'export': ('导出完整检查报告', 'Export full check report'),
    'search': ('搜索文件、字段或问题', 'Search file, field or finding'),
    'files': ('文件概况', 'Files'),
    'findings': ('问题清单', 'Findings'),
    'ready': ('先选文件夹。检查不会修改文件，也不会开始分析。', 'Choose a folder. Checking does not edit files or start analysis.'),
    'need_folder': ('请先选择数据文件夹。', 'Choose an existing input folder first.'),
    'busy': ('正在检查 / 导出…', 'Checking / exporting…'),
    'summary': ('错误 {error} · 需核对 {warning} · 提示 {info}。{next}', 'Errors {error} · Review {warning} · Notes {info}. {next}'),
    'blocked': ('请先修正错误，再运行分析。', 'Fix the errors before running analysis.'),
    'allowed': ('没有阻止分析的错误；提示仍需阅读。', 'No blocking errors; review the notes before analysing.'),
    'stale': ('文件夹已更改，下表仍是上次检查；请重新检查。', 'Folder changed. The previous check remains below; check again.'),
    'scope': ('搜索只改变显示，导出保留全部检查项。空白结果不补零，疑似重复不自动删除；有计划的复检可能内容相同。结果对应检查时读取的文件，编辑文件后需要重查。', 'Search only filters the display; exports include all findings. Missing results stay missing and duplicate candidates are retained. Planned repeats can match. Results describe the files read during the check; check again after editing them.'),
    'error': ('检查未完成', 'Check not completed'),
    'wait': ('请等待本次检查或导出完成。', 'Wait for this check or export to finish.'),
    'exported': ('已保存：{path}', 'Saved: {path}'),
}
REASONS_ZH = {
    'File is missing, unreadable or not UTF-8.': '文件缺失、无法读取，或不是 UTF-8 编码。',
    'SOURCE.json must declare data_type as synthetic.': 'SOURCE.json 中的 data_type 必须标记为 synthetic（模拟数据）。',
    'SOURCE.json is missing, unreadable or invalid JSON.': 'SOURCE.json 缺失、无法读取，或 JSON 格式错误。',
    'Expected exact documented columns and order.': '表头名称或顺序与数据字典不符。',
    'Incorrect number of cells.': '本行的字段数量与表头不同。',
    'Required value missing.': '必填值为空。',
    'Use YYYY-MM-DD.': '日期须为有效的 YYYY-MM-DD。',
    'Use a finite number without separators or unit text.': '请填写有限数值，如 100 或 98.5；不要加入分隔符或单位。',
    'Non-zero value is too small to store; it would become zero.': '这个非零数太小，存储时会变成零；已停止读入，请核对数值。',
    'Different ranges occur for the same product, test, method and unit; check which specification applies.': '同一产品、项目、方法和单位下出现不同范围；请核对适用的规格。对照值不是批准值，两条记录均保留。',
    'Duplicate primary key.': '记录编号重复。',
    'At least one batch is required.': '至少需要一条批次记录。',
    'Action predates deviation opening.': '措施创建日期早于偏差开启日期。',
    'Due date predates action creation.': '到期日期早于措施创建日期。',
    'Event predates batch manufacture.': '记录日期早于该批次生产日期。',
    'Orphan foreign key.': '找不到对应的批次或偏差编号。',
    'Completion/closure predates creation/opening.': '完成或关闭日期早于创建或开启日期。',
    'Result and specification units differ; no automatic conversion.': '检验值与范围的单位不一致，程序不会自动换算。',
    'Lower specification exceeds upper specification.': '下限高于上限。',
    'Result is missing, not zero.': '检验结果为空；保留为空，不当作零。',
    'Same measurement content under a different ID; check duplicate entry or planned repeat.': '编号不同但检验内容相同；请核对是重复录入，还是计划内复检。',
}


def reason_text(reason, language):
    if language != 'zh':
        return reason
    if reason.startswith('Malformed CSV:'):
        return 'CSV 无法完整解析：' + reason.split(':', 1)[1]
    return REASONS_ZH.get(reason, reason)


def export_check(result, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    write_input_report(result, destination)
    from review import field_label, display_value
    for lang, locale in (('en', 'en'), ('zh', 'zh-CN')):
        title = TEXT['title'][lang == 'en']
        body = f'<!doctype html><html lang="{locale}"><meta charset="utf-8"><title>{title}</title><style>body{{font:16px system-ui;max-width:1100px;margin:32px auto;padding:16px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccd8d2;padding:8px;text-align:left}}p{{overflow-wrap:anywhere}}</style><h1>{title}</h1><p>{html.escape(result["source"])}</p><p>{html.escape(result["checked_at_utc"])}</p><p>{TEXT["scope"][lang == "en"]}</p>'
        columns = INPUT_FINDING_COLUMNS
        body += '<table><tr>' + ''.join('<th>' + html.escape(field_label(key, lang)) + '</th>' for key in columns) + '</tr>'
        for row in result['findings']:
            body += '<tr>' + ''.join('<td>' + html.escape(reason_text(row[key], lang) if key == 'reason'
                                      else display_value(key, row[key], lang)) + '</td>' for key in columns) + '</tr>'
        body += '</table></html>'
        (destination / ('INPUT_CHECK.' + locale + '.html')).write_text(body, encoding='utf-8')
    (destination / 'manifest.json').write_text(json.dumps({
        'complete': True, 'kind': 'input-check', 'input_sha256': result['input_sha256'],
        'artifacts': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(destination.iterdir()) if p.is_file()}
    }, indent=2), encoding='utf-8')
    return destination


class InputCheckWindow:
    def __init__(self, owner, factory):
        self.owner, self.result, self.checked_folder = owner, None, None
        self.busy, self.poll_id = False, None
        self.events = queue.Queue()
        self.window = tk.Toplevel(owner.root)
        self.window.transient(owner.root)
        self.window.geometry(f'1100x{min(800, owner.root.winfo_screenheight()-100)}')
        self.window.minsize(850, 600)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.window.bind('<Destroy>', self.destroyed, add='+')
        frame = ttk.Frame(self.window, padding=18)
        frame.pack(fill='both', expand=True)
        self.title = ttk.Label(frame, style='Title.TLabel')
        self.title.pack(anchor='w')
        self.folder = tk.StringVar(value=owner.inputs.get())
        self.entry = ttk.Entry(frame, textvariable=self.folder)
        self.entry.pack(fill='x', pady=8)
        self.controls = ttk.Frame(frame)
        self.controls.pack(fill='x')
        self.buttons = {}
        for index, (key, command) in enumerate((('browse', self.browse), ('check', self.check), ('export', self.export))):
            button = ttk.Button(self.controls, command=command)
            button.grid(row=0, column=index, sticky='w', padx=(0,6), pady=2)
            self.buttons[key] = button
        self.controls.bind('<Configure>', self.layout_buttons)
        self.status = ttk.Label(frame, wraplength=1000)
        self.status.pack(fill='x', pady=8)
        self.search_label = ttk.Label(frame)
        self.search_label.pack(anchor='w', pady=(12, 4))
        self.search = tk.StringVar()
        ttk.Entry(frame, textvariable=self.search).pack(fill='x', pady=(0,6))
        self.note = ttk.Label(frame, wraplength=1000, style='Muted.TLabel')
        self.note.pack(side='bottom', fill='x', pady=(8, 0))
        self.notebook = ttk.Notebook(frame)
        self.notebook.pack(fill='both', expand=True)
        findings, files = ttk.Frame(self.notebook), ttk.Frame(self.notebook)
        self.notebook.add(findings)
        self.notebook.add(files)
        self.finding_table = factory(findings, owner, self.open_finding)
        self.finding_table.priority = INPUT_FINDING_COLUMNS
        self.finding_table.tree.configure(height=6)
        self.profile_table = factory(files, owner)
        self.profile_table.priority = ['table', 'readable_records', 'missing_results']
        self.profile_table.tree.configure(height=4)
        frame.bind('<Configure>', self.wrap)
        self.folder.trace_add('write', lambda *args: self.render_status())
        self.search.trace_add('write', lambda *args: self.refresh())
        self.apply_view()

    def text(self, key, **values):
        return TEXT[key][self.owner.language == 'en'].format(**values)

    def stale(self):
        return self.result is not None and self.folder.get().strip() != self.checked_folder

    def apply_view(self):
        self.window.title('BatchScope · ' + self.text('title'))
        self.window.configure(background=self.owner.colors['background'])
        self.title.configure(text=self.text('title'))
        self.search_label.configure(text=self.text('search'))
        self.note.configure(text=self.text('scope'))
        self.notebook.tab(0, text=self.text('findings'))
        self.notebook.tab(1, text=self.text('files'))
        for key, button in self.buttons.items():
            button.configure(text=self.text(key))
        self.profile_table.populate(self.result['profiles'] if self.result else [], preserve=True)
        self.refresh()
        self.render_status()
        self.layout_buttons()

    def layout_buttons(self, event=None):
        width = event.width if event is not None else self.controls.winfo_width()
        row, column, used = 0, 0, 0
        for button in self.buttons.values():
            size = button.winfo_reqwidth() + 6
            if used and used + size > width:
                row, column, used = row+1, 0, 0
            button.grid_configure(row=row, column=column)
            used, column = used+size, column+1

    def render_status(self):
        if self.busy:
            text = self.text('busy')
        elif self.stale():
            text = self.text('stale')
        elif self.result:
            text = self.text('summary', **self.result['counts'], next=self.text('allowed' if self.result['can_analyse'] else 'blocked'))
        else:
            text = self.text('ready')
        self.status.configure(text=text)
        self.entry.configure(state='disabled' if self.busy else 'normal')
        for key, button in self.buttons.items():
            enabled = not self.busy and (key != 'export' or self.result is not None and not self.stale())
            button.configure(state='normal' if enabled else 'disabled')

    def refresh(self):
        from review import display_value
        needle = self.search.get().strip().casefold()
        rows = []
        for source in self.result['findings'] if self.result else []:
            row = dict(source, reason=reason_text(source['reason'], self.owner.language))
            searchable = ' '.join(str(v) for v in row.values()) + ' ' + ' '.join(
                display_value(key, value, self.owner.language) for key, value in row.items())
            if not needle or needle in searchable.casefold():
                rows.append(row)
        self.finding_table.populate(rows)

    def open_finding(self):
        row = self.finding_table.selected()
        if row is None:
            return
        from review import field_label, display_value
        from tkinter.scrolledtext import ScrolledText
        window = tk.Toplevel(self.window)
        window.title(self.text('findings'))
        window.transient(self.window)
        window.geometry('760x430')
        window.minsize(460, 280)
        text = ScrolledText(window, wrap='word', font='TkDefaultFont', padx=16, pady=16,
                            background=self.owner.colors['surface'], foreground=self.owner.colors['text'])
        text.pack(fill='both', expand=True)
        body = '\n\n'.join(field_label(key, self.owner.language) + ': ' +
                           display_value(key, row[key], self.owner.language) for key in self.finding_table.priority)
        text.insert('1.0', body)
        text.configure(state='disabled')
        return window

    def browse(self):
        folder = filedialog.askdirectory(parent=self.window)
        if folder:
            self.folder.set(folder)

    def launch(self, kind, operation):
        if self.busy:
            return
        self.busy = True
        self.render_status()
        def work():
            try:
                self.events.put((True, kind, operation()))
            except Exception as exc:
                self.events.put((False, kind, str(exc)))
        threading.Thread(target=work, daemon=True).start()
        self.poll_id = self.window.after(50, self.poll)

    def check(self):
        if self.busy:
            return
        folder = self.folder.get().strip()
        if not folder or not Path(folder).is_dir():
            messagebox.showinfo(self.text('title'), self.text('need_folder'), parent=self.window)
            return
        self.running_folder = folder
        self.launch('check', lambda: input_report(check_inputs(folder)))

    def export(self):
        if self.busy or self.result is None or self.stale():
            return
        parent = filedialog.askdirectory(parent=self.window)
        if parent:
            result = deepcopy(self.result)
            def work():
                reserved = Path(tempfile.mkdtemp(prefix='BatchScope-input-check-', dir=parent))
                return export_check(result, reserved / 'report')
            self.launch('export', work)

    def poll(self):
        self.poll_id = None
        try:
            ok, kind, value = self.events.get_nowait()
        except queue.Empty:
            self.poll_id = self.window.after(50, self.poll)
            return
        self.busy = False
        if ok and kind == 'check':
            self.result, self.checked_folder = value, self.running_folder
            self.apply_view()
        elif ok:
            self.render_status()
            self.status.configure(text=self.text('exported', path=value))
        else:
            self.render_status()
            messagebox.showerror(self.text('error'), value, parent=self.window)

    def wrap(self, event):
        for label in (self.status, self.note, self.title):
            label.configure(wraplength=max(400, event.width-36))

    def confirm_close(self):
        if self.busy:
            messagebox.showinfo(self.text('title'), self.text('wait'), parent=self.window)
            return False
        return True

    def close(self):
        if self.confirm_close():
            self.window.destroy()

    def destroyed(self, event):
        if event.widget is self.window and self.poll_id is not None:
            self.window.after_cancel(self.poll_id)
            self.poll_id = None
