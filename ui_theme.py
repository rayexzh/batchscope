"""Native font sizing, restrained ttk palettes and Windows DPI awareness."""
import ctypes
import sys
import tkinter.font as tkfont
from tkinter import ttk

PALETTES = {
    "light": {"background": "#edf3f6", "surface": "#ffffff", "text": "#18313e", "muted": "#526978",
              "header": "#dce9ee", "accent": "#126d78", "selection": "#145b73", "stripe": "#f2f7f9", "border": "#bed0d8"},
    "dark": {"background": "#14212b", "surface": "#1d303d", "text": "#e6eff5", "muted": "#aec2cf",
             "header": "#2b4353", "accent": "#126d78", "selection": "#236b86", "stripe": "#223847", "border": "#496473"},
}


def enable_dpi_awareness():
    """Call before creating Tk; existing process awareness is left in place."""
    if sys.platform == "win32":
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except (AttributeError, OSError):
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except (AttributeError, OSError):
                pass


def apply_theme(root, name="light", font_size=11):
    colors = PALETTES[name]
    families = set(tkfont.families(root))
    family = next((f for f in ("Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", "Arial") if f in families), "TkDefaultFont")
    for font_name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        tkfont.nametofont(font_name, root).configure(family=family, size=font_size)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=colors["background"], foreground=colors["text"], font="TkDefaultFont")
    style.configure("TFrame", background=colors["background"])
    style.configure("Card.TFrame", background=colors["surface"], borderwidth=1, relief="solid")
    style.configure("TLabel", background=colors["background"], foreground=colors["text"])
    style.configure("Muted.TLabel", foreground=colors["muted"])
    style.configure("Title.TLabel", font=(family, min(18, font_size+7), "bold"))
    style.configure("Card.TLabel", background=colors["surface"], foreground=colors["muted"])
    style.configure("Value.TLabel", background=colors["surface"], foreground=colors["text"], font=(family, font_size+7, "bold"))
    style.configure("TButton", padding=(12, 7), background=colors["header"], foreground=colors["text"], bordercolor=colors["border"])
    style.map("TButton", background=[("active", colors["selection"])], foreground=[("disabled", colors["muted"]), ("active", "#ffffff")])
    style.configure("Primary.TButton", background=colors["accent"], foreground="#ffffff")
    style.map("Primary.TButton", background=[("disabled", colors["header"]), ("active", colors["selection"])], foreground=[("disabled", colors["muted"])])
    for control in ("TEntry", "TCombobox"):
        style.configure(control, fieldbackground=colors["surface"], foreground=colors["text"], background=colors["header"], padding=6,
                        selectbackground=colors["selection"], selectforeground="#ffffff", bordercolor=colors["border"], arrowcolor=colors["text"])
        style.map(control, fieldbackground=[("readonly", colors["surface"]), ("disabled", colors["header"])],
                  foreground=[("disabled", colors["muted"]), ("readonly", colors["text"])])
    root.option_add("*TCombobox*Listbox.background", colors["surface"])
    root.option_add("*TCombobox*Listbox.foreground", colors["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", colors["selection"])
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
    root.option_add("*TCombobox*Listbox.font", "TkDefaultFont")
    height = tkfont.nametofont("TkDefaultFont", root).metrics("linespace") + 14
    style.configure("Treeview", background=colors["surface"], fieldbackground=colors["surface"], foreground=colors["text"],
                    rowheight=height, bordercolor=colors["border"], font="TkDefaultFont")
    style.map("Treeview", background=[("selected", colors["selection"])], foreground=[("selected", "#ffffff")])
    style.configure("Treeview.Heading", background=colors["header"], foreground=colors["text"], padding=(9, 9), font=(family, font_size, "bold"))
    style.map("Treeview.Heading", background=[("active", colors["selection"])], foreground=[("active", "#ffffff")])
    style.configure("TNotebook", background=colors["background"], borderwidth=0)
    style.configure("TNotebook.Tab", padding=(16, 9), background=colors["header"], foreground=colors["muted"])
    style.map("TNotebook.Tab", background=[("selected", colors["surface"])], foreground=[("selected", colors["text"])])
    style.configure("Horizontal.TProgressbar", background=colors["accent"], troughcolor=colors["header"])
    style.configure("TScrollbar", background=colors["header"], troughcolor=colors["background"], arrowcolor=colors["text"])
    root.configure(background=colors["background"])
    return colors
