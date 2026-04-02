"""
cmd_open.py — rr open [CODE]
Open the project F: drive folder in Windows Explorer.
Looks up the path from Project_Master_Index.csv, falls back to F: drive scan.
"""

import os
import csv
import subprocess
from .utils import DB_INDEX, PROJECT_ROOT, c


def run(args):
    if not args:
        print(c("red", "Usage: rr open [CODE]"))
        return

    code = args[0].upper()
    path = None

    # 1. Try Project_Master_Index.csv
    if DB_INDEX.exists():
        with open(str(DB_INDEX), encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if row.get("Code", "").upper() == code:
                    raw = row.get("F: Drive Path", "").replace("/", "\\")
                    if raw and os.path.exists(raw):
                        path = raw
                    break

    # 2. Fallback: scan F:/Projects for CODE_ prefix
    if not path and PROJECT_ROOT.exists():
        for entry in os.listdir(str(PROJECT_ROOT)):
            if entry.upper().startswith(code + "_") or entry.upper() == code:
                candidate = PROJECT_ROOT / entry
                if candidate.is_dir():
                    path = str(candidate)
                    break

    if not path:
        print(c("red", f"Project '{code}' not found or path inaccessible."))
        print(c("grey", f"  Searched index: {DB_INDEX}"))
        print(c("grey", f"  Searched F: drive: {PROJECT_ROOT}"))
        return

    print(c("green_fg", f"Opening: {path}"))
    subprocess.Popen(["explorer", path])
