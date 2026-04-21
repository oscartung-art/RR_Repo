#!/usr/bin/env python3
"""
Helper to display ingest-schedule final enriched review table.
Usage: python display_schedule_preview.py "<PDF_PATH>" ["<OUT_DIR>"]
"""
import os
import sys
import csv
import subprocess
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: python display_schedule_preview.py '<PDF_PATH>' ['<OUT_DIR>']")
    sys.exit(1)

# Find repo root (this script is in tools/, so parent is root)
REPO_ROOT = Path(__file__).parent.parent
pdf_path = Path(sys.argv[1]).expanduser()
out_dir_arg = sys.argv[2] if len(sys.argv) > 2 else None
if out_dir_arg:
    out_dir = Path(out_dir_arg).expanduser()
else:
    out_dir_str = input("Output folder for .metadata.efu: ").strip().strip('"')
    if not out_dir_str:
        print("ERROR: Output folder is required.")
        sys.exit(1)
    out_dir = Path(out_dir_str).expanduser()

# Load API key from environment or API.env
env = os.environ.copy()
if not env.get('OPENROUTER_API_KEY'):
    try:
        api_env = (REPO_ROOT / "API.env").read_text()
        for line in api_env.split('\n'):
            line = line.strip()
            if line.startswith('sk-or'):
                env['OPENROUTER_API_KEY'] = line
                break
    except Exception:
        pass

# Run ingest_schedule with --csv flag (AI enrichment enabled by default)
# Use the same Python interpreter that's running this script
python_exe = sys.executable
ingest_schedule_path = REPO_ROOT / "tools" / "ingest_schedule.py"

result = subprocess.run(
    [python_exe, str(ingest_schedule_path), str(pdf_path), "--csv", "--out", str(out_dir)],
    capture_output=True, text=True, timeout=120, cwd=str(REPO_ROOT),
    env=env
)

if result.returncode != 0:
    print("ERROR:", result.stderr)
    sys.exit(1)

# Parse CSV
lines = result.stdout.strip().split('\n')
reader = list(csv.DictReader(iter(lines)))

# Get summary from stderr
summary_lines = result.stderr.strip().split('\n')
project = client = album = entries = ""
for line in summary_lines:
    if line.startswith("Project :"):
        project = line.replace("Project :", "").strip()
    elif line.startswith("Client  :"):
        client = line.replace("Client  :", "").strip()
    elif line.startswith("Album   :"):
        album = line.replace("Album   :", "").strip()
    elif line.startswith("Entries :"):
        entries = line.replace("Entries :", "").strip()

# Display
print("\n" + "="*140)
if project:
    print(f"Project: {project}")
if client:
    print(f"Client: {client}")
if album:
    print(f"Album: {album}")
if entries:
    print(f"Entries: {entries}")
print("="*140 + "\n")

# Show table with all enriched columns - compact, aligned format
print("Final enriched result (before EFU write):\n")
if reader:
    columns = list(reader[0].keys())
    rows_list = list(reader)
    
    # Calculate proper column widths
    col_widths = {}
    for col in columns:
        max_width = len(col)
        for row in rows_list:
            val = row[col] if row[col] != '-' else ''
            max_width = max(max_width, len(str(val)))
        col_widths[col] = min(max_width + 1, 30)  # Add 1 for padding, cap at 30
    
    # Print header with proper alignment
    header_parts = []
    for col in columns:
        header_parts.append(f"{col:<{col_widths[col]}s}")
    print("".join(header_parts))
    
    # Print rows with proper alignment
    for row in rows_list:
        row_parts = []
        for col in columns:
            val = row[col] if row[col] != '-' else ''
            row_parts.append(f"{str(val):<{col_widths[col]}s}")
        print("".join(row_parts))

print("\n" + "="*140)
