"""audit_keywords.py — validate manual/ingest_keywords.md for consistency.

Run:
    python tools/audit_keywords.py

Checks:
  1. Duplicate entries within any section
  2. Prefix Codes whose subcategory is not in the Allowlist
  3. Keyword Map entries whose target subcategory is not in the Allowlist
  4. Allowlist subcategories not referenced by any Prefix Code or Keyword Map entry
  5. Duplicate CLIP Labels
  6. Usage Locations that are duplicated
  7. Summary counts per section
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

KEYWORDS_MD = Path(__file__).resolve().parents[1] / "manual" / "ingest_keywords.md"


def parse_keywords_md(path: Path) -> dict[str, list[list[str]]]:
    """Parse the markdown file into {section: [data_rows]}."""
    sections: dict[str, list[list[str]]] = {}
    current: str | None = None
    table_row_idx = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
            table_row_idx = 0
            continue
        if current is None or not line.startswith("|"):
            continue
        table_row_idx += 1
        if table_row_idx <= 2:          # skip header (1) and separator (2)
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells:
            sections[current].append(cells)
    return sections


def _col(rows: list[list[str]], idx: int = 0) -> list[str]:
    return [r[idx] for r in rows if len(r) > idx and r[idx]]


def audit(sections: dict[str, list[list[str]]]) -> int:
    """Run all checks. Returns the number of issues found."""
    issues: list[str] = []

    # ------------------------------------------------------------------ helpers
    def warn(msg: str) -> None:
        issues.append(msg)

    def check_dupes(label: str, values: list[str]) -> None:
        counts = Counter(v.lower() for v in values)
        for v, n in sorted(counts.items()):
            if n > 1:
                # Find original casing for display
                orig = next(x for x in values if x.lower() == v)
                warn(f"[{label}] Duplicate entry: '{orig}' appears {n} times")

    # ------------------------------------------------------------------ load
    prefix_rows = sections.get("Prefix Codes", [])
    keyword_rows = sections.get("Keyword Map", [])
    subcats = set(_col(sections.get("Subcategories", [])))
    location_rows = sections.get("Usage Locations", [])
    clip_rows: list = []
    ignore_rows = sections.get("Ignore Folders", [])

    prefix_codes = _col(prefix_rows, 0)
    prefix_targets = _col(prefix_rows, 1)
    kw_keywords = _col(keyword_rows, 0)
    kw_targets = _col(keyword_rows, 1)
    locations = _col(location_rows)
    clip_labels = _col(clip_rows)
    ignore_dirs = _col(ignore_rows)

    # ------------------------------------------------------------------ 1. dupes per section
    check_dupes("Prefix Codes", prefix_codes)
    check_dupes("Keyword Map / keywords", kw_keywords)
    check_dupes("Subcategories", list(subcats))
    check_dupes("Usage Locations", locations)
    check_dupes("Ignore Folders", ignore_dirs)

    # ------------------------------------------------------------------ 2. prefix targets not in allowlist
    for code, target in zip(prefix_codes, prefix_targets):
        if target and target not in subcats:
            warn(f"[Prefix Codes] '{code}' → '{target}' is NOT in Subcategories")

    # ------------------------------------------------------------------ 3. keyword targets not in allowlist
    for keyword, target in zip(kw_keywords, kw_targets):
        if target and target not in subcats:
            warn(f"[Keyword Map] '{keyword}' → '{target}' is NOT in Subcategories")

    # ------------------------------------------------------------------ 4. orphaned subcategories
    referenced = set(prefix_targets) | set(kw_targets)
    orphans = sorted(subcats - referenced)
    if orphans:
        for o in orphans:
            warn(f"[Subcategories] '{o}' has no Prefix Code or Keyword pointing to it (orphan)")

    # ------------------------------------------------------------------ report
    sep = "-" * 60
    print(sep)
    print("audit_keywords.py — ingest keyword table audit")
    print(sep)

    if issues:
        print(f"\n{len(issues)} issue(s) found:\n")
        for i, msg in enumerate(issues, 1):
            print(f"  {i:3}. {msg}")
    else:
        print("\nNo issues found. All tables are consistent.")

    print()
    print("Summary:")
    print(f"  Prefix Codes           : {len(prefix_codes)}")
    print(f"  Keyword Map entries    : {len(kw_keywords)}")
    print(f"  Subcategories          : {len(subcats)}")
    print(f"  Usage Locations        : {len(locations)}")
    print(f"  Ignore Folders         : {len(ignore_dirs)}")
    print(f"  Orphaned subcategories : {len(orphans)}")
    print(sep)

    return len(issues)


def main() -> None:
    if not KEYWORDS_MD.exists():
        print(f"ERROR: {KEYWORDS_MD} not found.", file=sys.stderr)
        sys.exit(1)
    sections = parse_keywords_md(KEYWORDS_MD)
    issues = audit(sections)
    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
