"""
cmd_log.py — rr log [CODE] [message]
Append a timestamped entry to a project's CHANGELOG.md on F: drive.

Strategy for finding the project folder:
  1. Look for an exact match: F:/Projects/[CODE]_*
  2. Look for a case-insensitive prefix match
  3. If not found on F:, fall back to creating/appending in projects/[CODE].md log section
"""

import os
from datetime import datetime
from .utils import PROJECTS_DIR, PROJECT_ROOT, c


def _find_project_dir(code):
    """Return the F: drive project folder Path for the given code, or None."""
    if not PROJECT_ROOT.exists():
        return None
    code_upper = code.upper()
    for entry in os.listdir(str(PROJECT_ROOT)):
        # Match CODE_ prefix (case-insensitive)
        if entry.upper().startswith(code_upper + "_") or entry.upper() == code_upper:
            candidate = PROJECT_ROOT / entry
            if candidate.is_dir():
                return candidate
    return None


def run(args):
    if len(args) < 2:
        print(c("red", "Usage: rr log [CODE] [message]"))
        print(c("grey", "  Example: rr log PLS \"Client approved R03\""))
        return

    code    = args[0].upper()
    message = " ".join(args[1:])
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"- [{timestamp}] {message}\n"

    # Try F: drive first
    project_dir = _find_project_dir(code)

    if project_dir:
        changelog = project_dir / "CHANGELOG.md"
        if not changelog.exists():
            with open(str(changelog), "w", encoding="utf-8") as f:
                f.write(f"# {code} — Changelog\n\n")
        with open(str(changelog), "a", encoding="utf-8") as f:
            f.write(entry)
        print(c("green_fg", f"Logged to F: drive → {changelog}"))
        print(c("grey",     f"  {entry.strip()}"))
        return

    # Fallback: log into projects/[CODE].md as a comment block
    project_md = PROJECTS_DIR / f"{code}.md"
    if not project_md.exists():
        print(c("red", f"Project '{code}' not found on F: drive or in projects/."))
        print(c("grey", f"  Searched: {PROJECT_ROOT}"))
        return

    # Append to end of the .md file
    with open(str(project_md), "a", encoding="utf-8") as f:
        f.write(f"\n<!-- LOG {timestamp} -->\n<!-- {message} -->\n")
    print(c("yellow", f"F: drive not found. Logged to projects/{code}.md instead."))
    print(c("grey",   f"  {entry.strip()}"))
