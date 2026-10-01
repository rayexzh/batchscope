"""Desktop review with language, theme, readable tables and record actions."""
from collections import Counter
from pathlib import Path
import os
import queue
import tempfile
import threading
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

from quality_ops import analyse, generate, iso_date
from comparison import compare
from review import (FILTERS, REPORT_LABELS, STATUS_LABELS, describe_group,
                    clipboard_row, display_value, field_label, filter_details, group_details, local_label)
from ui_text import tr
from ui_theme import apply_theme, enable_dpi_awareness
from runtime_paths import output_root
from workbench_ui import WorkbenchWindow
from audit_ui import AuditWindow
from timeline_ui import TimelineWindow

ROOT = Path(__file__).resolve().parent
PRIORITY = ["product", "test_type", "outside_range_records", "outside_range_pct", "missing_records",
            "judgeable_records", "measured_records", "category", "open_records", "oldest_open_days",
            "metric", "before_value", "after_value", "delta", "change",
            "action_id", "test_id", "deviation_id", "batch_id", "before_status", "after_status", "snapshot_status", "value", "overdue_days"]


class RecordTable:
    """Stable row IDs preserve record identity through sorting and language changes."""
    def __init__(self, parent, owner, detail_action=None):
        self.owner, self.detail_action = owner, detail_action
        self.detail_label = "details"
        self.priority = PRIORITY
        self.rows, self.sort_state = [], None
        self.tree = ttk.Treeview(parent, show="headings", selectmode="browse", height=5)
        y = ttk.Scrollbar(parent, command=self.tree.yview)
        x = ttk.Scrollbar(parent, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y.set, xscrollcommand=x.set)
        y.pack(side="right", fill="y")
        x.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)
        self.menu = tk.Menu(self.tree, tearoff=False)
        self.tree.bind("<Button-3>", self.popup)
        self.tree.bind("<Control-c>", lambda event: self.copy_row())
        self.tree.bind("<Return>", lambda event: self.open_row())
        self.tree.bind("<Double-1>", self.double_click)

    def selected(self):
        selection = self.tree.selection()
        return self.rows[int(selection[0])] if selection else None

    def populate(self, rows, preserve=False):
        selected = self.tree.selection() if preserve else ()
        self.rows = list(rows)
        self.tree.delete(*self.tree.get_children())
        if not preserve:
            self.sort_state = None
        columns = list(rows[0]) if rows else []
        self.columns = [key for key in self.priority if key in columns] + [key for key in columns if key not in self.priority]
        self.tree.configure(columns=self.columns)
        font = tkfont.nametofont("TkDefaultFont", self.tree)
        for col in self.columns:
            label = field_label(col, self.owner.language)
            content_width = max((font.measure(display_value(col, row[col], self.owner.language))
                                 for row in rows[:60]), default=0)
            width = max(105, min(560 if col == "change" else 280, max(font.measure(label), content_width) + 28))
            if col in ("product", "method", "closed_on_source", "completed_on_source"):
                width = max(width, 170)
            self.tree.heading(col, text=label, command=lambda column=col: self.sort(column))
            self.tree.column(col, width=width, minwidth=75, stretch=False)
        for index, row in enumerate(rows):
            self.tree.insert("", "end", iid=str(index), tags=("even" if index % 2 == 0 else "odd",),
                             values=[display_value(key, row[key], self.owner.language) for key in self.columns])
        self.retheme()
        if selected and self.tree.exists(selected[0]):
            self.tree.selection_set(selected)
        if self.sort_state and self.sort_state[0] in self.columns:
            self.sort(*self.sort_state)

    def sort(self, column, descending=None):
        if descending is None:
            descending = self.sort_state is not None and self.sort_state == (column, False)
        self.sort_state = (column, descending)
        present = [i for i, row in enumerate(self.rows) if row[column] is not None]
        missing = [i for i, row in enumerate(self.rows) if row[column] is None]
        # Each schema column has one type; numeric values sort numerically, NULL stays last.
        present.sort(key=lambda i: self.rows[i][column].casefold() if isinstance(self.rows[i][column], str)
                     else self.rows[i][column], reverse=descending)
        for position, index in enumerate(present + missing):
            self.tree.move(str(index), "", position)
            self.tree.item(str(index), tags=("even" if position % 2 == 0 else "odd",))
        for col in self.columns:
            arrow = (" ▼" if descending else " ▲") if col == column else ""
            self.tree.heading(col, text=field_label(col, self.owner.language) + arrow)

    def retheme(self):
        colors = self.owner.colors
        self.tree.tag_configure("even", background=colors["surface"])
        self.tree.tag_configure("odd", background=colors["stripe"])
        self.menu.configure(background=colors["surface"], foreground=colors["text"],
                            activebackground=colors["selection"], activeforeground="#ffffff",
                            font="TkMenuFont")
        self.menu.delete(0, "end")
        if self.detail_action:
            self.menu.add_command(label=self.owner.t(self.detail_label), command=self.open_row)
            self.menu.add_separator()
        self.menu.add_command(label=self.owner.t("copy_row"), command=self.copy_row)
        self.menu.add_command(label=self.owner.t("copy_id"), command=self.copy_id)

    def select_at(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return False
        self.tree.selection_set(item)
        self.tree.focus(item)
        self.tree.focus_set()
        return True

    def popup(self, event):
        if not self.select_at(event):
            return
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def double_click(self, event):
        if self.select_at(event):
            self.open_row()

    def open_row(self):
        if self.detail_action and self.selected() is not None:
            return self.detail_action()

    def copy_row(self):
        row = self.selected()
        if row is not None:
            text = clipboard_row(self.columns, row, self.owner.language)
            self.copy(text, "copy_done")
        return "break"

    def copy_id(self):
        row = self.selected()
        if row is not None:
            for key in ("event_id", "action_id", "test_id", "deviation_id", "batch_id", "product"):
                if key in row:
                    self.copy(str(row[key]), "copy_id_done")
                    break

    def copy(self, text, notice):
        self.tree.clipboard_clear()
        self.tree.clipboard_append(text)
        self.owner.notice = notice
        self.owner.render_status()


class DetailWindow:
    def __init__(self, owner, result, report, selected):
        self.owner, self.rows = owner, group_details(result, report, selected)
        self.report, self.as_of, self.selected_group = report, result["as_of"], selected
        self.window = tk.Toplevel(owner.root)
        self.window.geometry(f"1150x{min(780, owner.root.winfo_screenheight()-100)}")
        self.window.transient(owner.root)
        frame = ttk.Frame(self.window, padding=20)
        frame.pack(fill="both", expand=True)
        self.title = ttk.Label(frame, style="Title.TLabel")
        self.title.pack(anchor="w")
        self.description = ttk.Label(frame, wraplength=1050, style="Muted.TLabel")
        self.description.pack(anchor="w", pady=10)
        controls = ttk.Frame(frame)
        controls.pack(fill="x", pady=6)
        self.status_label = ttk.Label(controls)
        self.status_label.pack(side="left", padx=(0, 8))
        self.status_filter = ttk.Combobox(controls, state="readonly", width=24)
        self.status_filter.pack(side="left")
        self.status_filter.bind("<<ComboboxSelected>>", lambda event: self.refresh())
        self.search_label = ttk.Label(controls)
        self.search_label.pack(side="left", padx=(16, 8))
        self.search = tk.StringVar()
        ttk.Entry(controls, textvariable=self.search).pack(side="left", fill="x", expand=True)
        self.search.trace_add("write", lambda *args: self.refresh())
        self.counts = tk.StringVar()
        ttk.Label(frame, textvariable=self.counts, wraplength=1050).pack(anchor="w", pady=8)
        area = ttk.Frame(frame)
        area.pack(fill="both", expand=True)
        self.table = RecordTable(area, owner)
        self.tree = self.table.tree
        self.note = ttk.Label(frame, wraplength=1050, style="Muted.TLabel")
        self.note.pack(side="bottom", anchor="w", pady=10, before=area)
        self.apply_view()

    def apply_view(self):
        lang = self.owner.language
        label = local_label(REPORT_LABELS[self.report], lang)
        self.window.title(f"{label} · {self.as_of}")
        self.window.configure(background=self.owner.colors["background"])
        self.title.configure(text=label)
        self.description.configure(text=self.owner.t("snapshot", date=self.as_of) + "\n" + describe_group(self.report, self.selected_group, lang))
        self.status_label.configure(text=self.owner.t("status"))
        self.search_label.configure(text=self.owner.t("search"))
        index = max(0, self.status_filter.current())
        self.status_filter.configure(values=[self.owner.t("all")] + [local_label(STATUS_LABELS[s], lang) for s in FILTERS[self.report]])
        self.status_filter.current(index)
        self.note.configure(text=self.owner.t("source_dates"))
        self.refresh(preserve=True)

    def refresh(self, preserve=False):
        index = self.status_filter.current()
        status = FILTERS[self.report][index-1] if index > 0 else None
        self.visible_rows = filter_details(self.rows, status, self.search.get())
        self.table.populate(self.visible_rows, preserve=preserve)
        counts = Counter(row["snapshot_status"] for row in self.rows)
        breakdown = " · ".join(f"{local_label(STATUS_LABELS[s], self.owner.language)}: {counts[s]}" for s in FILTERS[self.report])
        self.counts.set(self.owner.t("showing", visible=len(self.visible_rows), total=len(self.rows)) + "\n" + self.owner.t("full_group") + ": " + breakdown)


class ComparisonWindow:
    """A fixed two-date result, independent of later edits in the main window."""
    def __init__(self, owner, comparison):
        self.owner, self.result = owner, comparison
        self.window = tk.Toplevel(owner.root)
        self.window.geometry(f"1150x{min(850, owner.root.winfo_screenheight()-100)}")
        self.window.minsize(850, 600)
        self.window.transient(owner.root)
        self.canvas = tk.Canvas(self.window, highlightthickness=0)
        scroll = ttk.Scrollbar(self.window, command=self.canvas.yview)
        scroll.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.pack(fill="both", expand=True)
        frame = ttk.Frame(self.canvas, padding=18)
        canvas_window = self.canvas.create_window((0, 0), window=frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfigure(canvas_window, width=event.width))
        self.window.bind("<MouseWheel>", self.scroll_page, add="+")
        self.title = ttk.Label(frame, style="Title.TLabel")
        self.title.pack(anchor="w")
        self.dates = ttk.Label(frame, style="Muted.TLabel")
        self.dates.pack(anchor="w", pady=8)
        self.summary = ttk.Label(frame, wraplength=1050)
        self.summary.pack(anchor="w", pady=6)
        controls = ttk.Frame(frame)
        controls.pack(fill="x", pady=8)
        self.changed = tk.BooleanVar(value=True)
        self.changed_check = ttk.Checkbutton(controls, variable=self.changed, command=self.refresh)
        self.changed_check.pack(anchor="w")
        self.search = tk.StringVar()
        self.search_label = ttk.Label(controls)
        self.search_label.pack(side="left", padx=(0, 8))
        ttk.Entry(controls, textvariable=self.search).pack(side="left", fill="x", expand=True)
        self.counts = ttk.Label(frame)
        self.counts.pack(anchor="w", pady=6)
        self.note = ttk.Label(frame, style="Muted.TLabel", wraplength=1050)
        self.note.pack(side="bottom", fill="x", pady=(10, 0))
        self.book = ttk.Notebook(frame)
        self.book.pack(fill="both", expand=True)
        self.tables = {}
        for key in ("metrics", "deviations", "actions", "measurements"):
            tab = ttk.Frame(self.book)
            self.book.add(tab)
            self.tables[key] = RecordTable(tab, owner)
            self.tables[key].priority = ["metric", "before_value", "after_value", "delta",
                                         "action_id", "deviation_id", "test_id", "batch_id", "product",
                                         "change", "before_status", "after_status"]
            if key == "metrics":
                self.tables[key].tree.configure(height=6)
        self.search.trace_add("write", lambda *args: self.refresh())
        self.book.bind("<<NotebookTabChanged>>", lambda event: self.refresh())
        frame.bind("<Configure>", lambda event: self.wrap(event.width))
        self.apply_view()

    def wrap(self, width):
        for label in (self.title, self.dates, self.summary, self.counts, self.note):
            label.configure(wraplength=max(400, width-36))
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def scroll_page(self, event):
        if not isinstance(event.widget, ttk.Treeview) and event.delta:
            self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
            return "break"

    def apply_view(self):
        self.window.title("BatchScope · " + self.owner.t("comparison"))
        self.window.configure(background=self.owner.colors["background"])
        self.canvas.configure(background=self.owner.colors["background"])
        self.title.configure(text=self.owner.t("comparison"))
        self.dates.configure(text=self.owner.t("comparison_dates", start=self.result["from_date"], end=self.result["to_date"]))
        counts = Counter(row["change"] for key in ("deviations", "actions", "measurements") for row in self.result[key])
        self.summary.configure(text=" · ".join(f"{self.owner.t(k)}: {v}" for k, v in counts.items()) or self.owner.t("all") + ": 0")
        self.changed_check.configure(text=self.owner.t("changed_only"))
        self.search_label.configure(text=self.owner.t("search"))
        self.note.configure(text=self.owner.t("compare_note"))
        for index, key in enumerate(self.tables):
            self.book.tab(index, text=self.owner.t("comparison_" + key))
        self.refresh(preserve=True)

    def refresh(self, preserve=False):
        needle = self.search.get().strip().casefold()
        self.visible_rows = {}
        for key, table in self.tables.items():
            rows = self.result[key]
            shown = [row for row in rows
                     if (not self.changed.get() or row.get("change") not in ("still_open", "still_overdue"))
                     and (not needle or any(needle in display_value(k, v).casefold() for k, v in row.items()))]
            self.visible_rows[key] = shown
            table.populate(shown, preserve=preserve)
        key = list(self.tables)[self.book.index("current")]
        self.counts.configure(text=self.owner.t("comparison_count", visible=len(self.visible_rows[key]), total=len(self.result[key])))


class Window:
    def __init__(self, root):
        self.root, self.events = root, queue.Queue()
        self.busy, self.output, self.result = False, None, None
        self.result_inputs = self.running_inputs = None
        self.language, self.theme, self.font_size = "zh", "light", 11
        self.phase, self.error, self.notice = "ready", "", None
        self.details = []
        self.comparisons = []
        self.review_views = []
        self.colors = apply_theme(root, self.theme, self.font_size)
        root.geometry(f"1120x{min(1050, root.winfo_screenheight()-100)}")
        root.minsize(900, 600)
        self.canvas = tk.Canvas(root, highlightthickness=0, background=self.colors["background"])
        scroll = ttk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        scroll.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.pack(fill="both", expand=True)
        frame = ttk.Frame(self.canvas, padding=22)
        self.canvas_window = self.canvas.create_window((0, 0), window=frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfigure(self.canvas_window, width=event.width))
        root.bind("<MouseWheel>", self.scroll_page, add="+")
        header = ttk.Frame(frame)
        header.pack(fill="x")
        self.title = ttk.Label(header, style="Title.TLabel")
        self.title.pack(anchor="w")
        toolbar = ttk.Frame(header)
        toolbar.pack(fill="x", pady=(5, 0))
        review_toolbar = ttk.Frame(header)
        review_toolbar.pack(fill="x", pady=(8, 0))
        self.work_button = ttk.Button(review_toolbar, command=self.open_workbench, state="disabled")
        self.work_button.pack(side="left")
        self.report_button = ttk.Button(review_toolbar, command=self.open_review_report, state="disabled")
        self.report_button.pack(side="left", padx=8)
        extra_toolbar = ttk.Frame(header)
        extra_toolbar.pack(fill="x", pady=(6, 0))
        self.audit_button = ttk.Button(extra_toolbar, command=self.open_audit)
        self.audit_button.pack(side="left")
        self.timeline_button = ttk.Button(extra_toolbar, command=self.open_timeline)
        self.timeline_button.pack(side="left", padx=8)
        self.language_button = ttk.Button(toolbar, command=self.toggle_language)
        self.language_button.pack(side="right")
        self.theme_button = ttk.Button(toolbar, command=self.toggle_theme)
        self.theme_button.pack(side="right", padx=7)
        ttk.Button(toolbar, text="A+", width=3, command=lambda: self.adjust_font(1)).pack(side="right")
        ttk.Button(toolbar, text="A−", width=3, command=lambda: self.adjust_font(-1)).pack(side="right", padx=5)
        self.subtitle = ttk.Label(frame, style="Muted.TLabel")
        self.subtitle.pack(anchor="w", pady=(6, 14))
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(0, 8))
        self.generate_button = ttk.Button(row, command=self.create_data)
        self.generate_button.pack(side="left")
        self.browse_button = ttk.Button(row, command=self.choose)
        self.browse_button.pack(side="left", padx=8)
        self.inputs = tk.StringVar()
        self.input_entry = ttk.Entry(frame, textvariable=self.inputs)
        self.input_entry.pack(fill="x")
        self.date_row = row = ttk.Frame(frame)
        row.pack(fill="x", pady=12)
        self.date_label = ttk.Label(row)
        self.date_label.pack(side="left", padx=(0, 9))
        self.as_of = tk.StringVar(value="2026-06-30")
        self.date_entry = ttk.Entry(row, textvariable=self.as_of, width=13)
        self.date_entry.pack(side="left")
        self.run_button = ttk.Button(row, command=self.start, style="Primary.TButton")
        self.run_button.pack(side="left", padx=10)
        self.open_button = ttk.Button(row, command=self.open_folder, state="disabled")
        self.open_button.pack(side="right")
        self.comparison_row = row = ttk.Frame(frame)
        row.pack(fill="x", pady=(0, 10))
        self.from_label = ttk.Label(row)
        self.from_label.pack(side="left", padx=(0, 9))
        self.from_date = tk.StringVar(value="2026-05-31")
        self.from_entry = ttk.Entry(row, textvariable=self.from_date, width=13)
        self.from_entry.pack(side="left")
        self.compare_button = ttk.Button(row, command=lambda: self.start(comparison=True))
        self.compare_button.pack(side="left", padx=10)
        self.view_compare_button = ttk.Button(row, command=self.open_comparison, state="disabled")
        self.view_compare_button.pack(side="right")
        self.compare_to = ttk.Label(frame, style="Muted.TLabel")
        self.compare_to.pack(anchor="w", pady=(0, 8))
        self.status = tk.StringVar()
        self.status_label = ttk.Label(frame, textvariable=self.status, wraplength=1060, style="Muted.TLabel")
        self.status_label.pack(anchor="w", pady=(0, 10))
        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.card_row = ttk.Frame(frame)
        self.card_row.pack(fill="x", pady=(0, 14))
        self.metric_cards = {}
        self.card_frames = []
        for index, key in enumerate(("measured_records", "judgeable_records", "missing_records", "outside_range_records", "open_deviations", "overdue_actions")):
            self.card_row.columnconfigure(index, weight=1, uniform="metrics")
            card = ttk.Frame(self.card_row, style="Card.TFrame", padding=(12, 9))
            self.card_frames.append(card)
            card.grid(row=0, column=index, sticky="nsew", padx=(0, 6 if index<5 else 0))
            value = ttk.Label(card, text="—", style="Value.TLabel")
            value.pack(anchor="w")
            label = ttk.Label(card, style="Card.TLabel")
            card.bind("<Configure>", lambda event, text=label: text.configure(wraplength=max(70, event.width-24)))
            label.pack(anchor="w")
            self.metric_cards[key] = (value, label)
        self.card_row.bind("<Configure>", lambda event: self.layout_cards(event.width))
        self.metrics = tk.StringVar()
        controls = ttk.Frame(frame)
        controls.pack(fill="x", pady=(0, 7))
        self.hint = ttk.Label(controls, style="Muted.TLabel")
        self.hint.pack(side="left", fill="x", expand=True)
        self.detail_button = ttk.Button(controls, command=self.open_selected_details, state="disabled")
        self.detail_button.pack(side="right")
        controls.bind("<Configure>", lambda event: self.hint.configure(wraplength=max(200, event.width-self.detail_button.winfo_reqwidth()-16)))
        self.book = ttk.Notebook(frame)
        self.book.pack(fill="both", expand=True)
        self.tables, self.record_tables = {}, {}
        for key in ("01_test_ranges", "02_deviation_backlog", "03_overdue_actions"):
            tab = ttk.Frame(self.book)
            self.book.add(tab)
            table = RecordTable(tab, self, lambda report=key: self.open_details(report))
            self.record_tables[key], self.tables[key] = table, table.tree
        self.scope = ttk.Label(frame, wraplength=1060, style="Muted.TLabel")
        self.scope.pack(side="bottom", anchor="w", pady=(12, 0), before=self.book)
        frame.bind("<Configure>", self.resize_text)
        for variable in (self.inputs, self.as_of, self.from_date):
            variable.trace_add("write", lambda *args: self.render_status())
        self.apply_view()
        self.poll_id = root.after(100, self.poll)
        root.bind("<Destroy>", self.on_destroy, add="+")
        root.protocol("WM_DELETE_WINDOW", self.close)

    def t(self, key, **values):
        return tr(key, self.language, **values)

    def apply_view(self):
        self.colors = apply_theme(self.root, self.theme, self.font_size)
        self.canvas.configure(background=self.colors["background"])
        self.root.title(self.t("title") + " — Synthetic Demo")
        for key in ("title", "subtitle", "hint", "scope"):
            getattr(self, key).configure(text=self.t(key))
        for widget, key in ((self.generate_button,"generate"), (self.browse_button,"browse"),
                            (self.date_label,"as_of"), (self.run_button,"analyse"),
                            (self.from_label,"from_date"), (self.compare_button,"compare"),
                            (self.compare_to,"compare_to"), (self.view_compare_button,"view_comparison"),
                            (self.open_button,"results"), (self.detail_button,"details")):
            widget.configure(text=self.t(key))
        self.work_button.configure(text=self.t("workbench"))
        self.report_button.configure(text=self.t("open_review"))
        self.audit_button.configure(text="审计日志复核" if self.language == "zh" else "Audit log review")
        self.timeline_button.configure(text="多日期对比" if self.language == "zh" else "Multi-date review")
        self.language_button.configure(text="English" if self.language == "zh" else "中文")
        self.theme_button.configure(text=self.t("dark" if self.theme == "light" else "light"))
        for key, (value, label) in self.metric_cards.items():
            label.configure(text=self.t(key))
            value.configure(text=str(self.result["metrics"][key]) if self.result else "—")
        for index, (key, table) in enumerate(self.record_tables.items()):
            self.book.tab(index, text=self.t(key))
            rows = self.result["reports"][key] if self.result else []
            table.populate(rows, preserve=True)
        self.render_status()
        self.layout_date_controls()
        self.details = [d for d in self.details if d.window.winfo_exists()]
        for detail in self.details:
            detail.apply_view()
        self.comparisons = [c for c in self.comparisons if c.window.winfo_exists()]
        for comparison in self.comparisons:
            comparison.apply_view()
        self.review_views = [view for view in self.review_views if view.window.winfo_exists()]
        for view in self.review_views:
            view.apply_view()

    def toggle_language(self):
        self.language = "en" if self.language == "zh" else "zh"
        self.apply_view()

    def resize_text(self, event):
        width = max(400, event.width-44)
        for label in (self.title, self.subtitle, self.status_label, self.scope):
            label.configure(wraplength=width)
        self.layout_date_controls()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def layout_date_controls(self):
        for frame, label, entry, run, result in (
            (self.date_row, self.date_label, self.date_entry, self.run_button, self.open_button),
            (self.comparison_row, self.from_label, self.from_entry, self.compare_button, self.view_compare_button),
        ):
            widgets = (label, entry, run, result)
            for widget in widgets:
                if widget.winfo_manager() == "pack":
                    widget.pack_forget()
            required = sum(widget.winfo_reqwidth() for widget in widgets) + 40
            wide = frame.winfo_width() >= required
            for column in range(4):
                frame.columnconfigure(column, weight=1 if wide and column == 2 else 0)
            label.grid(row=0, column=0, sticky="w", padx=(0,8), pady=(0,6))
            entry.grid(row=0, column=1, sticky="w", padx=(0,8), pady=(0,6))
            run.grid(row=0 if wide else 1, column=2 if wide else 0, sticky="w", padx=(0,8), pady=(0,6))
            result.grid(row=0 if wide else 1, column=3 if wide else 1, sticky="w", pady=(0,6))

    def scroll_page(self, event):
        # Tables/comboboxes keep their own wheel behaviour; the surrounding page scrolls.
        if isinstance(event.widget, (ttk.Treeview, ttk.Combobox)) or event.delta == 0:
            return None
        self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"

    def layout_cards(self, width):
        # Large fonts and narrow windows use two rows rather than clipping labels.
        required = max(card.winfo_reqwidth() for card in self.card_frames) * 6 + 30
        columns = 6 if width >= required else 3
        for index in range(6):
            self.card_row.columnconfigure(index, weight=1 if index < columns else 0,
                                          uniform="metrics" if index < columns else "", minsize=0)
        for index, card in enumerate(self.card_frames):
            card.grid_configure(row=index // columns, column=index % columns,
                                padx=(0, 6 if index % columns < columns-1 else 0), pady=(0, 6))

    def toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"
        self.apply_view()

    def adjust_font(self, change):
        self.font_size = min(14, max(10, self.font_size + change))
        self.apply_view()

    def render_status(self):
        if self.phase == "completed":
            text = f"{self.t('completed')} · {self.result['as_of']}\n{self.output}"
            if "comparison" in self.result:
                comparison = self.result["comparison"]
                text = self.t("completed") + " · " + self.t("comparison_dates", start=comparison["from_date"], end=comparison["to_date"]) + f"\n{self.output}"
        elif self.phase == "failed":
            text = f"{self.t('failed')}: {self.error}\n{self.t('partial')}"
        else:
            text = self.t(self.phase)
        if self.notice:
            text += " · " + self.t(self.notice)
        if self.phase == "completed" and self.result_inputs:
            folder, as_of, start = self.result_inputs
            text += "\n" + self.t("snapshot_input", folder=folder)
            current = (str(Path(self.inputs.get().strip()).resolve()), self.as_of.get().strip(),
                       self.from_date.get().strip() if start is not None else None)
            if current != self.result_inputs:
                text = self.t("inputs_changed") + "\n" + text
        self.status.set(text)

    def choose(self):
        folder = filedialog.askdirectory(title=self.t("folder_dialog"))
        if folder:
            self.inputs.set(folder)

    def create_data(self):
        try:
            parent = output_root(ROOT)
            parent.mkdir(parents=True, exist_ok=True)
            folder = Path(tempfile.mkdtemp(prefix="demo-", dir=parent)) / "inputs"
            generate(folder)
            self.inputs.set(str(folder))
            if self.result is None:
                self.phase, self.notice = "generated", None
                self.render_status()
        except (OSError, ValueError) as exc:
            messagebox.showerror(self.t("failed"), str(exc))

    def start(self, comparison=False):
        if self.busy:
            return
        folder, as_of = Path(self.inputs.get().strip()), self.as_of.get().strip()
        if not self.inputs.get().strip() or not folder.is_dir():
            messagebox.showerror(self.t("check_input"), self.t("select_input"))
            return
        from_date = self.from_date.get().strip()
        try:
            iso_date(as_of)
            if comparison and iso_date(from_date) > iso_date(as_of):
                raise ValueError(self.t("date_order"))
        except ValueError:
            messagebox.showerror(self.t("check_input"), self.t("date_help"))
            return
        try:
            parent = output_root(ROOT)
            parent.mkdir(parents=True, exist_ok=True)
            output = Path(tempfile.mkdtemp(prefix="review-", dir=parent)) / "results"
        except OSError as exc:
            messagebox.showerror(self.t("failed"), str(exc))
            return
        from_date = self.from_date.get().strip()
        self.busy, self.output, self.result = True, None, None
        self.running_inputs = (str(folder.resolve()), as_of, from_date if comparison else None)
        self.phase, self.notice = "working", None
        self.metrics.set("")
        for control in (self.run_button, self.generate_button, self.browse_button, self.date_entry, self.input_entry, self.open_button, self.detail_button, self.compare_button, self.from_entry, self.view_compare_button, self.work_button, self.report_button, self.audit_button, self.timeline_button):
            control.configure(state="disabled")
        self.apply_view()
        self.progress.pack(fill="x", pady=(0, 8), before=self.card_row)
        self.progress.start()
        target = self.comparison_worker if comparison else self.worker
        args = (folder, output, from_date, as_of) if comparison else (folder, output, as_of)
        threading.Thread(target=target, args=args, daemon=True).start()

    def comparison_worker(self, inputs, output, from_date, to_date):
        try:
            self.events.put((True, output, compare(inputs, output, from_date, to_date)))
        except Exception as exc:
            self.events.put((False, output, str(exc)))

    def worker(self, inputs, output, as_of):
        try:
            self.events.put((True, output, analyse(inputs, output, as_of)))
        except Exception as exc:
            self.events.put((False, output, str(exc)))

    def poll(self):
        try:
            ok, output, result = self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy = False
            self.progress.stop()
            self.progress.pack_forget()
            for control in (self.run_button, self.generate_button, self.browse_button, self.date_entry, self.input_entry, self.compare_button, self.from_entry, self.audit_button, self.timeline_button):
                control.configure(state="normal")
            self.output = output if output.exists() else None
            self.open_button.configure(state="normal" if self.output else "disabled")
            self.detail_button.configure(state="normal" if ok else "disabled")
            self.work_button.configure(state="normal" if ok else "disabled")
            self.report_button.configure(state="normal" if ok else "disabled")
            if ok:
                self.result, self.phase = result, "completed"
                self.result_inputs = self.running_inputs
                self.metrics.set(str(result["metrics"]))
            else:
                self.error, self.phase = result, "failed"
            self.apply_view()
            self.view_compare_button.configure(state="normal" if ok and "comparison" in result else "disabled")
            if ok and "comparison" in result:
                self.open_comparison()
        self.poll_id = self.root.after(100, self.poll)

    def on_destroy(self, event):
        if event.widget is self.root and self.poll_id is not None:
            try:
                self.root.after_cancel(self.poll_id)
            except tk.TclError:
                pass
            self.poll_id = None

    def open_selected_details(self):
        return self.open_details(list(self.tables)[self.book.index("current")])

    def open_details(self, report, event=None):
        if self.busy or self.result is None:
            return None
        table = self.record_tables[report]
        if event is not None and not table.select_at(event):
            return None
        row = table.selected()
        if row is None:
            messagebox.showinfo(self.t("details"), self.t("select_row"))
            return None
        detail = DetailWindow(self, self.result, report, row)
        self.details.append(detail)
        return detail

    def open_folder(self):
        if self.output:
            try:
                os.startfile(self.output)
            except (OSError, AttributeError) as exc:
                messagebox.showinfo(self.t("results"), f"{self.output}\n{exc}")

    def open_comparison(self):
        if self.busy or not self.result or "comparison" not in self.result:
            return None
        view = ComparisonWindow(self, self.result["comparison"])
        self.comparisons.append(view)
        return view

    def open_audit(self):
        if self.busy:
            return None
        view = AuditWindow(self, RecordTable)
        self.review_views.append(view)
        return view

    def open_timeline(self):
        if self.busy:
            return None
        view = TimelineWindow(self, RecordTable, inputs=self.inputs.get().strip())
        self.review_views.append(view)
        return view

    def open_workbench(self):
        if self.busy or not self.result or "operations" not in self.result:
            return None
        view = WorkbenchWindow(self, self.result, RecordTable)
        self.review_views.append(view)
        return view

    def open_review_report(self):
        if self.busy or not self.result or not self.output:
            return
        folder = self.output / "end_snapshot" if "comparison" in self.result else self.output
        try:
            os.startfile(folder / "QUALITY_REVIEW.html")
        except (OSError, AttributeError) as exc:
            messagebox.showerror(self.t("open_review"), str(exc))

    def close(self):
        if self.busy:
            messagebox.showinfo(self.t("running"), self.t("wait_close"))
        else:
            self.root.destroy()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--self-test":
        from exe_smoke import self_test
        sys.exit(self_test(Path(sys.argv[2])))
    enable_dpi_awareness()
    root = tk.Tk()
    Window(root)
    root.mainloop()
