#!/usr/bin/env python3
"""
csvlook.py — Pretty-print CSV files in the terminal.

Displays a CSV with aligned columns for quick inspection.
Handles .metadata.efu format (quoted CSV with headers).

Usage:
    python tools/csvlook.py <file.csv> [--lines N]
    python tools/csvlook.py Database/.metadata.efu
    python tools/csvlook.py db/masterdb.csv --lines 20
"""
import sys
import csv
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    max_lines = None
    if len(sys.argv) >= 4 and sys.argv[2] == "--lines":
        max_lines = int(sys.argv[3])

    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}")
        sys.exit(1)

    # Read CSV
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("(empty file)")
        sys.exit(0)

    # Calculate column widths
    cols = reader.fieldnames or []
    if not cols:
        print("(no headers)")
        sys.exit(0)

    widths = {}
    for col in cols:
        widths[col] = len(col)
        for row in rows[:50]:  # check first 50 rows for width
            val = str(row.get(col, ""))
            widths[col] = max(widths[col], len(val))
        # Cap width to keep it readable
        widths[col] = min(widths[col], 40)

    # Print header
    print()
    header = "  ".join(f"{col:<{widths[col]}}" for col in cols)
    print("\033[1m" + header + "\033[0m")
    print("  ".join("-" * widths[col] for col in cols))

    # Print rows
    count = 0
    for row in rows:
        if max_lines is not None and count >= max_lines:
            break
        parts = []
        for col in cols:
            val = str(row.get(col, ""))
            if len(val) > widths[col]:
                val = val[:widths[col] - 3] + "..."
            parts.append(f"{val:<{widths[col]}}")
        print("  ".join(parts))
        count += 1

    print()
    total = len(rows)
    if max_lines and total > max_lines:
        print(f"Showing {max_lines} of {total} total rows")
    else:
        print(f"Total: {total} rows")
    print()


if __name__ == "__main__":
    main()
