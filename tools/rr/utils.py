"""
utils.py — Shared helpers for the rr CLI
  - ANSI colour helpers
  - YAML front matter parser (no third-party deps)
  - Repo path bootstrap
"""

import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo root bootstrap — works regardless of cwd when rr is invoked
# ---------------------------------------------------------------------------
# tools/rr/utils.py  ->  tools/rr/  ->  tools/  ->  repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Shared.config import BRAIN_ROOT, PROJECT_ROOT

PROJECTS_DIR = BRAIN_ROOT / "projects"
CRM_PATH     = BRAIN_ROOT / "db" / "Master_CRM.csv"
DB_INDEX     = BRAIN_ROOT / "db" / "Project_Master_Index.csv"

# ---------------------------------------------------------------------------
# ANSI colour helpers
# ---------------------------------------------------------------------------
_ANSI = {
    "cyan":    "\033[1;36m",
    "green":   "\033[1;32m",
    "yellow":  "\033[33m",
    "grey":    "\033[90m",
    "red":     "\033[91m",
    "white":   "\033[1;37m",
    "bold":    "\033[1m",
    "reset":   "\033[0m",
    "red_bg":  "\033[1;41m",
    "green_fg":"\033[92m",
}

def c(colour, text):
    """Wrap text in an ANSI colour code."""
    return f"{_ANSI.get(colour, '')}{text}{_ANSI['reset']}"

def print_row(label, value, width=18):
    """Print a labelled row with consistent column alignment."""
    disp = c("grey", "-") if not value or str(value).strip() in ("-", "") else str(value)
    print(f"  {c('cyan', f'{label:<{width}}')} {disp}")

# ---------------------------------------------------------------------------
# YAML front matter parser (stdlib only)
# ---------------------------------------------------------------------------
def parse_front_matter(filepath):
    """
    Parse nested YAML front matter from a Markdown file.
    Returns a dict, or None if no front matter found.
    Handles simple key: value and one level of nesting.
    """
    filepath = str(filepath)
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.search(r"^---\s*\n(.*?)\n---\s*", content, re.DOTALL | re.MULTILINE)
    if not match:
        return None

    raw_lines = match.group(1).splitlines()
    # Strip inline comments and blank lines
    lines = [l.split("#")[0].rstrip() for l in raw_lines if l.strip() and not l.lstrip().startswith("#")]

    def parse_block(index, current_indent):
        data = {}
        while index < len(lines):
            line = lines[index]
            indent = len(line) - len(line.lstrip())
            if indent < current_indent:
                break
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip().strip("'\"")
                if not val:
                    # Possibly a nested block
                    if index + 1 < len(lines):
                        next_indent = len(lines[index + 1]) - len(lines[index + 1].lstrip())
                        if next_indent > indent:
                            nested, index = parse_block(index + 1, next_indent)
                            data[key] = nested
                            continue
                else:
                    data[key] = val
            index += 1
        return data, index

    parsed, _ = parse_block(0, 0)
    return parsed
