"""Desktop review views; no recalculation or mutable file reads in open windows."""
import tkinter as tk
from tkinter import messagebox, ttk

from review import display_value
from workbench import batch_snapshot


class ReviewWindow:
    def build(self, owner, factory, keys, title):
        self.owner, self.title_key = owner, title
        self.window = tk.Toplevel(owner.root)
        self.window.transient(owner.root)
        self.window.geometry(f"1150x{min(850, owner.root.winfo_screenheight()-100)}")
        self.window.minsize(850, 600)
        self.canvas = tk.Canvas(self.window, highlightthickness=0)
        scroll = ttk.Scrollbar(self.window, command=self.canvas.yview)
        scroll.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.pack(fill="both", expand=True)
        self.frame = ttk.Frame(self.canvas, padding=18)
        canvas_window = self.canvas.create_window((0, 0), window=self.frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(canvas_window, width=e.width))
        self.window.bind("<MouseWheel>", self.scroll_page, add="+")
        self.title = ttk.Label(self.frame, style="Title.TLabel")
        self.title.pack(anchor="w")
        self.caption = ttk.Label(self.frame, style="Muted.TLabel")
        self.caption.pack(anchor="w", pady=10)
        self.controls = ttk.Frame(self.frame)
        self.controls.pack(fill="x", pady=8)
        self.search_label = ttk.Label(self.controls)
        self.search_label.pack(side="left", padx=(0, 8))
        self.search = tk.StringVar()
        ttk.Entry(self.controls, textvariable=self.search).pack(side="left", fill="x", expand=True)
        self.counts = ttk.Label(self.frame)
        self.counts.pack(anchor="w", pady=8)
        self.note = ttk.Label(self.frame, style="Muted.TLabel")
        self.note.pack(side="bottom", fill="x", pady=(10, 0))
        self.book = ttk.Notebook(self.frame)
        self.book.pack(fill="both", expand=True)
        self.tables = {}
        for key in keys:
            tab = ttk.Frame(self.book)
            self.book.add(tab)
            self.tables[key] = factory(tab, owner)
            self.tables[key].priority = ["action_id", "batch_id", "deviation_id", "test_id", "product", "snapshot_status", "due_on", "days_until_due", "parent_status", "period", "period_end", "opening_open", "opened_in_period", "closed_in_period", "ending_open"]
            self.tables[key].tree.configure(height=7)
        self.search.trace_add("write", lambda *args: self.refresh())
        self.book.bind("<<NotebookTabChanged>>", lambda event: self.refresh())
        self.frame.bind("<Configure>", self.wrap)

    def scroll_page(self, event):
        if not isinstance(event.widget, (ttk.Treeview, ttk.Combobox)) and event.delta:
            self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
            return "break"

    def wrap(self, event):
        for label in (self.title, self.caption, self.counts, self.note):
            label.configure(wraplength=max(400, event.width-36))
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def apply_common(self):
        self.window.title("BatchScope · " + self.owner.t(self.title_key))
        self.window.configure(background=self.owner.colors["background"])
        self.canvas.configure(background=self.owner.colors["background"])
        self.title.configure(text=self.owner.t(self.title_key))
        self.search_label.configure(text=self.owner.t("search"))
        self.note.configure(text=self.owner.t("review_scope"))

    def show_rows(self, rows, preserve):
        needle = self.search.get().strip().casefold()
        self.visible_rows = {}
        for key, table in self.tables.items():
            shown = [r for r in rows[key] if not needle or any(needle in display_value(k, v).casefold() for k,v in r.items())]
            self.visible_rows[key] = shown
            table.populate(shown, preserve=preserve)
        key = list(self.tables)[self.book.index("current")]
        self.counts.configure(text=self.owner.t("review_counts", shown=len(self.visible_rows[key]), total=len(self.rows[key])))


class WorkbenchWindow(ReviewWindow):
    CODES = ("review_focus", "review_all", "overdue", "due_today", "due_soon", "later", "review_closed_parent")

    def __init__(self, owner, result, factory):
        self.result, self.rows, self.factory = result, result["operations"], factory
        self.build(owner, factory, ("queue", "aging", "monthly"), "workbench")
        row = ttk.Frame(self.frame)
        row.pack(fill="x", pady=8, before=self.controls)
        self.filter_label = ttk.Label(row)
        self.filter_label.pack(side="left", padx=(0, 10))
        self.filter = ttk.Combobox(row, state="readonly", width=36)
        self.filter.pack(side="left")
        self.filter.bind("<<ComboboxSelected>>", lambda event: self.refresh())
        row = ttk.Frame(self.frame)
        row.pack(fill="x", pady=(0, 8), before=self.controls)
        self.batch = ttk.Combobox(row, state="readonly", width=13, values=[r["batch_id"] for r in self.rows["batches"]])
        self.batch.pack(side="left", padx=10)
        self.batch.bind("<<ComboboxSelected>>", self.choose_batch)
        self.batch_button = ttk.Button(row, command=self.open_batch)
        self.batch_button.pack(side="left")
        self.tables["queue"].detail_action = self.open_batch
        self.tables["queue"].detail_label = "batch360"
        self.apply_view()

    def apply_view(self):
        self.apply_common()
        index = max(0, self.filter.current())
        self.filter.configure(values=[self.owner.t(k) for k in self.CODES])
        self.filter.current(index)
        self.filter_label.configure(text=self.owner.t("queue_filter"))
        self.batch_button.configure(text=self.owner.t("batch360"))
        metrics = self.rows["metrics"]
        self.caption.configure(text=self.owner.t("snapshot", date=self.result["as_of"]) + "\n" + " · ".join(f"{self.owner.t(k)}: {v}" for k,v in metrics.items()) + "\n" + self.owner.t("review_hint"))
        for i,key in enumerate(self.tables):
            self.book.tab(i, text=self.owner.t("review_" + key))
        self.refresh(preserve=True)

    def refresh(self, preserve=False):
        if not hasattr(self, "filter"):
            return
        code = self.CODES[max(0, self.filter.current())]
        rows = self.rows.copy()
        rows["queue"] = [r for r in self.rows["queue"] if code == "review_all"
                         or (code == "review_focus" and r["snapshot_status"] in ("overdue", "due_today", "due_soon"))
                         or (code == "review_closed_parent" and r["closed_parent_followup"])
                         or r["snapshot_status"] == code]
        active = self.book.index("current") == 0
        if active:
            if not self.filter.winfo_manager():
                self.filter.pack(side="left")
            self.filter_label.configure(text=self.owner.t("queue_filter"))
        else:
            self.filter.pack_forget()
            self.filter_label.configure(text=self.owner.t("filter_inactive"))
        self.show_rows(rows, preserve)

    def choose_batch(self, event=None):
        self.tables["queue"].tree.selection_remove(self.tables["queue"].tree.selection())

    def open_batch(self):
        selected = self.tables["queue"].selected() if self.book.index("current") == 0 else None
        batch_id = selected["batch_id"] if selected else self.batch.get()
        if not batch_id:
            messagebox.showinfo(self.owner.t("batch360"), self.owner.t("select_batch"))
            return None
        view = BatchWindow(self.owner, self.result, batch_id, self.factory)
        self.owner.review_views.append(view)
        return view


class BatchWindow(ReviewWindow):
    def __init__(self, owner, result, batch_id, factory):
        self.result = batch_snapshot(result, batch_id)
        self.rows = self.result
        self.build(owner, factory, ("measurements", "deviations", "actions"), "batch360")
        self.apply_view()

    def apply_view(self):
        self.apply_common()
        batch = self.result["batch"]
        self.caption.configure(text=f"{batch['batch_id']} · {batch['product']}\n" + self.owner.t("snapshot", date=self.result["as_of"]))
        for i,key in enumerate(self.tables):
            self.book.tab(i, text=self.owner.t({"measurements":"01_test_ranges", "deviations":"02_deviation_backlog", "actions":"review_queue"}[key]))
        self.refresh(preserve=True)

    def refresh(self, preserve=False):
        self.show_rows(self.rows, preserve)
