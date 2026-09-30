"""Read-only bundled resources and persistent user output paths are distinct."""
import os
from pathlib import Path
import sys


RESOURCE_ROOT = Path(__file__).resolve().parent


def output_root(source_root=RESOURCE_ROOT):
    if getattr(sys, "frozen", False):
        local = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return local / "BatchScope" / "outputs"
    return Path(source_root) / "outputs"
