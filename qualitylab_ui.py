"""Bilingual desktop sandbox; calculations run off the Tk event thread."""
from copy import deepcopy
from pathlib import Path
import os
import queue
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from qualitylab import EDITABLE, Laboratory
from quality_ops import finite_number

TEXT = {
    'save_work': ('保存进度', 'Save progress'),
    'load_work': ('打开进度', 'Open progress'),
    'saved_work': ('进度已保存：{folder}', 'Progress saved: {folder}'),
    'scope': ('模拟实验，不改原始数据；假设范围不代表获批规格，不用于批次放行。', 'Synthetic experiments; source data stays unchanged. Hypothetical limits are not approved specifications or release criteria.'),
    'title': ('质量数据实验室', 'Quality data laboratory'),
    'edit': ('1. 选择并修改模拟记录', '1. Edit a synthetic record'),
    'compare': ('2. 情景对比', '2. Compare scenarios'),
    'recheck': ('3. 重复检验练习', '3. Recheck exercise'),
    'search': ('搜索检验 / 批次 / 产品', 'Search test / batch / product'),
    'selected': ('当前检验：{id} · 排队修改 {count} 条', 'Selected test: {id} · {count} queued records'),
    'original': ('保留的初始结果：{id} · {value} {unit} · 范围 {low}–{high} · {date}', 'Retained initial result: {id} · {value} {unit} · range {low}–{high} · {date}'),
    'stage': ('加入 / 更新修改', 'Stage / update change'),
    'restore': ('恢复选中记录', 'Restore selected'),
    'reset': ('清空实验，恢复原始情景', 'Reset entire experiment'),
    'date': ('两种情景共用截至日期', 'Shared as-of date'),
    'run': ('运行情景对比', 'Run comparison'),
    'export': ('导出实验', 'Export experiment'),
    'open': ('打开实验报告', 'Open experiment report'),
    'blank': ('空白检验值代表缺失，不是零。范围修改仅是假设。', 'Blank result means missing, not zero. Edited bounds are hypothetical.'),
    'ready': ('选择检验记录，修改后先加入队列，再运行对比。', 'Select a test, stage edits, then run the comparison.'),
    'stale': ('有未重新计算的修改；请重新运行，旧结果不能作为当前情景导出。', 'Settings changed. Run again before exporting the current scenario.'),
    'draft': ('表单修改尚未加入队列；请先加入，或恢复选中记录。', 'Form edits are not staged. Stage them or restore the selected record first.'),
    'repeat_draft': ('复检计划有未评价的修改；请重新评价后导出。', 'The recheck plan has unevaluated edits. Evaluate it again before exporting.'),
    'other_drafts': ('其他检验记录还有草稿：{ids}。切回对应记录处理后再导出。', 'Other tests have pending drafts: {ids}. Return to those records before exporting.'),
    'done': ('对比完成：{date} · 修改 {count} 条记录；下表为本次计算结果。', 'Compared at {date}: {count} edited records. Tables show this run.'),
    'busy': ('正在计算 / 导出，请稍候。', 'Calculating / exporting…'),
    'wait': ('实验正在运行，请等完成后再关闭。', 'Wait for the experiment to finish before closing.'),
    'discard': ('是否丢弃未导出的实验修改？', 'Discard experiment edits that have not been exported?'),
    'metrics': ('指标：原始 → 假设', 'Metrics: baseline → scenario'),
    'transitions': ('记录变化与修改依据', 'Record changes and settings'),
    'repeat_note': ('先设定练习轮次、范围和日期，再一次性评价。第 1 轮始终保留原始结果；后续范围可保持或收窄，不代表更准确。练习结果不写回质量指标，也不提供 OOS 调查或复检规程。', 'Set the exercise plan before evaluating. Attempt 1 always retains the original result. Later ranges may stay equal or narrow; that does not prove accuracy. Attempts do not enter the quality metrics. This is not an OOS investigation or retesting protocol.'),
    'rounds': ('总轮次（含原始）', 'Total attempts (including original)'),
    'reason': ('练习理由', 'Exercise reason'),
    'evaluate': ('评价预设练习', 'Evaluate planned exercise'),
    'ever_flagged': ('至少一次超范围：保留全部结果，不作放行判断。', 'At least one outside-range result: all attempts retained; no release verdict.'),
    'no_flagged': ('本次所列结果未触发超范围；不证明准确或合规。', 'No listed result is outside its range; this does not establish accuracy or compliance.'),
    'exported': ('实验已导出：{folder}', 'Experiment exported: {folder}'),
    'failure': ('实验未完成', 'Experiment not completed'),
}


class LaboratoryWindow:
    def __init__(self, owner, factory, database, as_of, expected_sha256, model=None):
        self.owner, self.factory = owner, factory
        self.model = model if model is not None else Laboratory(database, as_of, expected_sha256)
        self.originals = {row['test_id']: row for row in self.model.tests}
        self.result, self.output, self.exported_state = None, None, None
        self.rechecks, self.events = [], queue.Queue()
        self.busy, self.poll_id, self.selected_id = False, None, None
        self.record_forms, self.evaluated_plans = {}, {}
        self.loading_forms = True
        self.window = tk.Toplevel(owner.root)
        self.window.transient(owner.root)
        self.window.geometry(f'1150x{min(900, owner.root.winfo_screenheight()-100)}')
        self.window.minsize(850, 600)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.window.bind('<Destroy>', self.on_destroy, add='+')
        self.canvas = tk.Canvas(self.window, highlightthickness=0)
        scroll = ttk.Scrollbar(self.window, command=self.canvas.yview)
        scroll.pack(side='right', fill='y')
        self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.pack(fill='both', expand=True)
        frame = ttk.Frame(self.canvas, padding=18)
        item = self.canvas.create_window((0, 0), window=frame, anchor='nw')
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfigure(item, width=e.width))
        self.window.bind('<MouseWheel>', self.scroll, add='+')
        self.title = ttk.Label(frame, style='Title.TLabel')
        self.title.pack(anchor='w')
        self.scope = ttk.Label(frame, style='Muted.TLabel', wraplength=1050)
        self.scope.pack(fill='x', pady=8)
        controls = ttk.Frame(frame)
        controls.pack(fill='x')
        self.date_label = ttk.Label(controls)
        self.date_label.pack(anchor='w')
        self.as_of = tk.StringVar(value=as_of)
        self.date_entry = ttk.Entry(controls, textvariable=self.as_of, width=14)
        self.date_entry.pack(anchor='w', pady=4)
        self.buttons = {}
        action_row = ttk.Frame(controls)
        action_row.pack(fill='x', pady=4)
        self.action_row = action_row
        for key, command in [('run', self.run), ('export', self.export), ('open', self.open_report), ('save_work', self.save_work), ('load_work', self.load_work)]:
            button = ttk.Button(action_row, command=command)
            button.grid(row=0, column=len(self.buttons), sticky='w', padx=(0, 6), pady=2)
            self.buttons[key] = button
        action_row.bind('<Configure>', self.layout_actions)
        self.status = ttk.Label(frame, wraplength=1050)
        self.status.pack(fill='x', pady=8)
        self.selection_label = ttk.Label(frame, wraplength=1050)
        self.selection_label.pack(fill='x', pady=(0, 6))
        self.book = ttk.Notebook(frame)
        self.book.pack(fill='both', expand=True)
        edit, comparison, repeated = [ttk.Frame(self.book, padding=10) for _ in range(3)]
        for tab in (edit, comparison, repeated):
            self.book.add(tab)
        self.search_label = ttk.Label(edit)
        self.search_label.pack(anchor='w')
        self.search = tk.StringVar()
        ttk.Entry(edit, textvariable=self.search).pack(fill='x', pady=4)
        area = ttk.Frame(edit)
        area.pack(fill='both', expand=True)
        self.test_table = factory(area, owner)
        self.test_table.tree.configure(height=6)
        self.test_table.tree.bind('<<TreeviewSelect>>', self.select)
        self.fields, self.field_labels, self.field_entries = {}, {}, []
        form = ttk.Frame(edit)
        form.pack(fill='x')
        form.columnconfigure(1, weight=1)
        for index, key in enumerate(EDITABLE):
            label = ttk.Label(form)
            label.grid(row=index, column=0, sticky='w', padx=(0, 12), pady=3)
            variable = tk.StringVar()
            entry = ttk.Entry(form, textvariable=variable)
            entry.grid(row=index, column=1, sticky='ew', pady=3)
            self.fields[key], self.field_labels[key] = variable, label
            variable.trace_add('write', self.form_changed)
            self.field_entries.append(entry)
        self.blank_note = ttk.Label(edit, style='Muted.TLabel', wraplength=1000)
        self.blank_note.pack(fill='x', pady=5)
        for key, command in [('stage', self.stage), ('restore', self.restore), ('reset', self.reset)]:
            button = ttk.Button(edit, command=command)
            button.pack(anchor='w', pady=2)
            self.buttons[key] = button
        self.metric_label = ttk.Label(comparison)
        self.metric_label.pack(anchor='w')
        area = ttk.Frame(comparison)
        area.pack(fill='both', expand=True)
        self.metric_table = factory(area, owner)
        self.metric_table.priority = ['metric', 'baseline_count', 'scenario_count', 'delta']
        self.metric_table.tree.configure(height=6)
        self.transition_label = ttk.Label(comparison)
        self.transition_label.pack(anchor='w', pady=(12, 4))
        area = ttk.Frame(comparison)
        area.pack(fill='both', expand=True)
        self.transition_table = factory(area, owner)
        self.transition_table.tree.configure(height=6)
        self.repeat_note = ttk.Label(repeated, wraplength=1000, style='Muted.TLabel')
        self.repeat_note.pack(fill='x', pady=6)
        self.repeat_original = ttk.Label(repeated, wraplength=1000)
        self.repeat_original.pack(fill='x', pady=6)
        self.round_label = ttk.Label(repeated)
        self.round_label.pack(anchor='w')
        self.round_count = tk.StringVar(value='3')
        self.rounds = ttk.Combobox(repeated, textvariable=self.round_count, values=['2', '3'], state='readonly', width=6)
        self.rounds.set('3')
        self.rounds.pack(anchor='w', pady=4)
        self.reason_label = ttk.Label(repeated)
        self.reason_label.pack(anchor='w')
        self.reason = tk.StringVar()
        self.reason_entry = ttk.Entry(repeated, textvariable=self.reason)
        self.reason_entry.pack(fill='x', pady=4)
        self.repeat_fields, self.repeat_labels, self.repeat_entries = [], [], []
        for number in (2, 3):
            box = ttk.LabelFrame(repeated, padding=8)
            box.pack(fill='x', pady=5)
            box.columnconfigure(1, weight=1)
            self.repeat_labels.append(box)
            variables, entries = {}, []
            for index, key in enumerate(EDITABLE):
                label = ttk.Label(box)
                label.grid(row=index, column=0, sticky='w', padx=(0, 12), pady=3)
                variable = tk.StringVar()
                entry = ttk.Entry(box, textvariable=variable)
                entry.grid(row=index, column=1, sticky='ew', pady=3)
                variables[key] = variable
                entries.append(entry)
                self.field_labels[f'{number}-{key}'] = label
            self.repeat_fields.append(variables)
            self.repeat_entries.append(entries)
        self.buttons['evaluate'] = ttk.Button(repeated, command=self.evaluate)
        self.buttons['evaluate'].pack(anchor='w', pady=6)
        self.repeat_status = ttk.Label(repeated, wraplength=1000)
        self.repeat_status.pack(fill='x', pady=6)
        area = ttk.Frame(repeated)
        area.pack(fill='both', expand=True)
        self.repeat_table = factory(area, owner)
        self.repeat_table.priority = ['attempt', 'test_id', 'value', 'spec_low', 'spec_high', 'measured_on', 'snapshot_status', 'unit']
        self.repeat_table.tree.configure(height=4)
        for variable in [self.reason, self.round_count, *(v for fields in self.repeat_fields for v in fields.values())]:
            variable.trace_add('write', self.form_changed)
        self.as_of.trace_add('write', lambda *args: self.render_status())
        self.search.trace_add('write', lambda *args: self.refresh_tests())
        frame.bind('<Configure>', lambda e: self.wrap(e.width))
        self.loading_forms = False
        self.apply_view()
        self.refresh_tests()
        items = self.test_table.tree.get_children()
        if items:
            self.test_table.tree.selection_set(items[0])
            self.select()

    def save_work(self):
        if self.busy:
            return
        from lab_session import save_session
        path = filedialog.asksaveasfilename(parent=self.window, defaultextension='.bslab',
            filetypes=[('BatchScope progress', '*.bslab')])
        if not path:
            return
        self.cache_form()
        try:
            save_session(path, self.model, {'as_of': self.as_of.get().strip(),
                'selected_id': self.selected_id, 'forms': self.record_forms, 'rechecks': self.rechecks})
            self.status.configure(text=self.text('saved_work', folder=path))
        except (OSError, ValueError) as exc:
            messagebox.showerror(self.text('failure'), str(exc), parent=self.window)

    def load_work(self):
        if not self.busy:
            self.owner.open_lab_progress()

    def restore_progress(self, state):
        # History is recomputed from the saved plans, not deserialized numeric summaries.
        self.rechecks = [self.model.recheck(e['test_id'], e['planned_rounds'], e['reason']) for e in state['rechecks']]
        self.evaluated_plans = {}
        for exercise in self.rechecks:
            fields = exercise['planned_rounds']
            reference = self.default_plan(exercise['test_id'])
            reference.update(rounds=str(len(fields)+1), reason=exercise['reason'])
            reference['fields'][:len(fields)] = fields
            self.evaluated_plans[exercise['test_id']] = reference
        self.record_forms = deepcopy(state['forms'])
        self.as_of.set(state['as_of'])
        selected = state['selected_id']
        for item in self.test_table.tree.get_children():
            self.test_table.tree.selection_set(item)
            row = self.test_table.selected()
            if row and row['test_id'] == selected:
                break
        self.select(force=True)
        self.render_status()

    def text(self, key, **values):
        return TEXT[key][1 if self.owner.language == 'en' else 0].format(**values)

    def state(self):
        return self.model.revision, self.as_of.get().strip(), len(self.rechecks)

    def stale(self):
        return self.result is not None and (self.result['revision'] != self.model.revision or self.result['as_of'] != self.as_of.get().strip())

    def draft_dirty(self):
        if not self.selected_id:
            return False
        return self.main_dirty(self.selected_id, {key: variable.get() for key, variable in self.fields.items()})

    def main_dirty(self, test_id, form):
        current = self.model.current(test_id)
        for key, value in form.items():
            text = value.strip()
            if key == 'measured_on':
                if text != current[key]:
                    return True
            else:
                try:
                    value = None if not text and key == 'value' else finite_number(text)
                except ValueError:
                    return True
                if value != current[key]:
                    return True
        return False

    def default_plan(self, test_id):
        original = self.originals[test_id]
        fields = {key: '' if original[key] is None else str(original[key]) for key in EDITABLE}
        return {'rounds': '3', 'reason': '', 'fields': [dict(fields), dict(fields)]}

    def repeat_plan(self):
        return {'rounds': self.round_count.get(), 'reason': self.reason.get(),
                'fields': [{key: variable.get() for key, variable in fields.items()} for fields in self.repeat_fields]}

    def form_snapshot(self):
        return {'main': {key: variable.get() for key, variable in self.fields.items()}, 'repeat': self.repeat_plan()}

    def cache_form(self):
        if self.selected_id and not self.loading_forms:
            self.record_forms[self.selected_id] = self.form_snapshot()

    def form_changed(self, *args):
        if not self.loading_forms:
            self.cache_form()
            self.render_status()

    def pending(self):
        forms = dict(self.record_forms)
        if self.selected_id:
            forms[self.selected_id] = self.form_snapshot()
        main, repeated = set(), set()
        for test_id, form in forms.items():
            if self.main_dirty(test_id, form['main']):
                main.add(test_id)
            reference = self.evaluated_plans.get(test_id, self.default_plan(test_id))
            if form['repeat'] != reference:
                repeated.add(test_id)
        return main, repeated

    def apply_view(self):
        from review import field_label
        self.window.title('BatchScope · ' + self.text('title'))
        self.title.configure(text=self.text('title'))
        self.canvas.configure(background=self.owner.colors['background'])
        self.window.configure(background=self.owner.colors['background'])
        self.scope.configure(text=self.text('scope'))
        for key, widget in [('date', self.date_label), ('search', self.search_label), ('blank', self.blank_note),
                            ('metrics', self.metric_label), ('transitions', self.transition_label),
                            ('repeat_note', self.repeat_note), ('rounds', self.round_label), ('reason', self.reason_label)]:
            widget.configure(text=self.text(key))
        for key, button in self.buttons.items():
            button.configure(text=self.text(key))
        for index, key in enumerate(('edit', 'compare', 'recheck')):
            self.book.tab(index, text=self.text(key))
        for key, label in self.field_labels.items():
            label.configure(text=field_label(key.split('-', 1)[-1], self.owner.language))
        for index, label in enumerate(self.repeat_labels, 2):
            label.configure(text=('第 ' + str(index) + ' 轮' if self.owner.language == 'zh' else 'Attempt ' + str(index)))
        for table in (self.test_table, self.metric_table, self.transition_table, self.repeat_table):
            table.populate(table.rows, preserve=True)
        self.render_status()
        self.layout_actions()

    def layout_actions(self, event=None):
        width = event.width if event is not None else self.action_row.winfo_width()
        row, column, used = 0, 0, 0
        for key in ('run', 'export', 'open', 'save_work', 'load_work'):
            button = self.buttons[key]
            needed = button.winfo_reqwidth() + 6
            if used and used + needed > width:
                row, column, used = row + 1, 0, 0
            button.grid_configure(row=row, column=column)
            column, used = column + 1, used + needed

    def refresh_tests(self):
        needle = self.search.get().strip().casefold()
        rows = [row for row in self.model.tests if not needle or any(needle in str(value).casefold() for value in row.values())]
        self.test_table.populate(rows)

    def select(self, event=None, force=False):
        row = self.test_table.selected()
        if not row or self.busy or row['test_id'] == self.selected_id and not force:
            return
        if not force:
            self.cache_form()
        self.selected_id = row['test_id']
        current = self.model.current(self.selected_id)
        saved = self.record_forms.get(self.selected_id, {
            'main': {key: '' if current[key] is None else str(current[key]) for key in EDITABLE},
            'repeat': self.default_plan(self.selected_id)})
        self.loading_forms = True
        try:
            for key, variable in self.fields.items():
                variable.set(saved['main'][key])
            self.rounds.set(saved['repeat']['rounds'])
            self.reason.set(saved['repeat']['reason'])
            for variables, values in zip(self.repeat_fields, saved['repeat']['fields']):
                for key, variable in variables.items():
                    variable.set(values[key])
        finally:
            self.loading_forms = False
        self.cache_form()
        self.update_repeat_view()
        self.render_status()

    def selected_exercise(self):
        return next((row for row in reversed(self.rechecks) if row['test_id'] == self.selected_id), None)

    def update_repeat_view(self):
        exercise = self.selected_exercise()
        self.repeat_table.populate(exercise['attempts'] if exercise else [])

    def render_status(self):
        if not hasattr(self, 'buttons') or 'evaluate' not in self.buttons:
            return
        self.selection_label.configure(text=self.text('selected', id=self.selected_id or '—', count=len(self.model.changes)))
        if self.selected_id:
            original = self.originals[self.selected_id]
            self.repeat_original.configure(text=self.text('original', id=self.selected_id,
                value='—' if original['value'] is None else original['value'], unit=original['unit'],
                low=original['spec_low'], high=original['spec_high'], date=original['measured_on']))
        main, repeated = self.pending()
        key = ('busy' if self.busy else 'draft' if self.selected_id in main else
               'repeat_draft' if self.selected_id in repeated else 'other_drafts' if main or repeated else
               'stale' if self.stale() else 'done' if self.result else 'ready')
        self.status.configure(text=self.text(key, date=self.result['as_of'] if self.result else '',
                              count=len(self.model.changes), ids=', '.join(sorted((main | repeated) - {self.selected_id}))))
        exercise = self.selected_exercise()
        repeat_key = ('repeat_draft' if self.selected_id in repeated else
                      'ever_flagged' if exercise and exercise['any_outside_range'] else 'no_flagged' if exercise else None)
        self.repeat_status.configure(text=self.text(repeat_key) if repeat_key else '')
        self.set_states()

    def set_states(self):
        main, repeated = self.pending()
        for key, button in self.buttons.items():
            enabled = not self.busy
            if key in ('stage', 'restore', 'evaluate'):
                enabled = enabled and self.selected_id is not None
            if key == 'export':
                enabled = enabled and self.result is not None and not self.stale() and not main and not repeated
            if key in ('run', 'evaluate'):
                enabled = enabled and not main
            if key == 'open':
                enabled = enabled and self.output is not None
            button.configure(state='normal' if enabled else 'disabled')
        for entry in [self.date_entry, self.reason_entry, *self.field_entries]:
            entry.configure(state='disabled' if self.busy else 'normal')
        self.rounds.configure(state='disabled' if self.busy else 'readonly')
        for index, entries in enumerate(self.repeat_entries):
            for entry in entries:
                entry.configure(state='disabled' if self.busy or index == 1 and self.round_count.get() == '2' else 'normal')

    def stage(self):
        if self.busy or self.selected_id is None:
            return
        try:
            self.model.stage(self.selected_id, {key: value.get().strip() for key, value in self.fields.items()})
            self.render_status()
        except (ValueError, TypeError) as exc:
            messagebox.showerror(self.text('failure'), str(exc), parent=self.window)

    def restore(self):
        if not self.busy and self.selected_id:
            self.model.reset(self.selected_id)
            self.record_forms.pop(self.selected_id, None)
            self.evaluated_plans.pop(self.selected_id, None)
            self.select(force=True)

    def reset(self):
        if self.busy:
            return
        self.model.reset()
        self.record_forms.clear()
        self.evaluated_plans.clear()
        self.result, self.rechecks, self.output, self.exported_state = None, [], None, None
        self.as_of.set(self.model.as_of)
        for table in (self.metric_table, self.transition_table, self.repeat_table):
            table.populate([])
        self.repeat_status.configure(text='')
        self.select(force=True)
        self.render_status()

    def launch(self, kind, operation):
        if self.busy:
            return
        self.busy = True
        self.render_status()
        def worker():
            try:
                self.events.put((True, kind, operation()))
            except Exception as exc:
                self.events.put((False, kind, str(exc)))
        threading.Thread(target=worker, daemon=True).start()
        self.poll_id = self.window.after(50, self.poll)

    def run(self):
        if self.pending()[0]:
            self.render_status()
            return
        day = self.as_of.get().strip()
        self.launch('run', lambda: self.model.run(day))

    def evaluate(self):
        if self.selected_id is None or self.busy or self.pending()[0]:
            return
        test_id, day, reason = self.selected_id, self.as_of.get().strip(), self.reason.get()
        form = deepcopy(self.repeat_plan())
        plans = [{key: variable.get().strip() for key, variable in values.items()}
                 for values in self.repeat_fields[:int(self.round_count.get())-1]]
        def operation():
            exercise = self.model.recheck(test_id, plans, reason)
            return self.model.run(day), exercise, (test_id, form)
        self.launch('recheck', operation)

    def poll(self):
        self.poll_id = None
        try:
            success, kind, value = self.events.get_nowait()
        except queue.Empty:
            self.poll_id = self.window.after(50, self.poll)
            return
        self.busy = False
        if not success:
            messagebox.showerror(self.text('failure'), value, parent=self.window)
        elif kind == 'export':
            self.output, self.exported_state = value, self.state()
            self.status.configure(text=self.text('exported', folder=value))
        else:
            if kind == 'recheck':
                value, exercise, (test_id, form) = value
                self.evaluated_plans[test_id] = form
                self.rechecks.append(exercise)
                self.update_repeat_view()
            self.result = value
            self.metric_table.populate(value['metrics'])
            self.transition_table.populate(value['transitions'])
            if kind == 'run':
                self.book.select(1)
        if kind != 'export' or not success:
            self.render_status()
        self.set_states()

    def export(self):
        if self.busy or self.result is None or self.stale() or any(self.pending()):
            return
        parent = filedialog.askdirectory(parent=self.window, title=self.text('export'))
        if not parent:
            return
        result = deepcopy(self.result)
        result['rechecks'] = deepcopy(self.rechecks)
        def operation():
            reserved = Path(tempfile.mkdtemp(prefix='BatchScope-lab-', dir=parent))
            return self.model.export(result, reserved / 'experiment')
        self.launch('export', operation)

    def open_report(self):
        if self.output:
            try:
                os.startfile(self.output / ('LAB.zh-CN.html' if self.owner.language == 'zh' else 'LAB.en.html'))
            except OSError as exc:
                messagebox.showinfo(self.text('title'), str(exc), parent=self.window)

    def wrap(self, width):
        for label in (self.scope, self.status, self.selection_label, self.repeat_original, self.repeat_note, self.repeat_status, self.blank_note):
            label.configure(wraplength=max(400, width-40))
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def scroll(self, event):
        if not isinstance(event.widget, (ttk.Treeview, ttk.Combobox)) and event.delta:
            self.canvas.yview_scroll(-1 if event.delta > 0 else 1, 'units')
            return 'break'

    def confirm_close(self):
        if self.busy:
            messagebox.showinfo(self.text('title'), self.text('wait'), parent=self.window)
            return False
        if any(self.pending()) or (self.model.changes or self.rechecks) and self.exported_state != self.state():
            return messagebox.askyesno(self.text('title'), self.text('discard'), parent=self.window)
        return True

    def close(self):
        if self.confirm_close():
            self.window.destroy()

    def on_destroy(self, event):
        if event.widget is self.window and self.poll_id is not None:
            self.window.after_cancel(self.poll_id)
            self.poll_id = None
