#!/usr/bin/env python3
"""
edit_efu_metadata.py — Update any field in .metadata.efu for specified asset files.

The .metadata.efu is always expected to be co-located with the asset files.
No fallback to a central database EFU.

Usage:
    python edit_efu_metadata.py --field Rating --value 99 "G:\\DB\\mpm\\file1.jpg" "G:\\DB\\mpm\\file2.jpg"
    python edit_efu_metadata.py --field Subject --value "Fixture/Lighting/SpotLight" "G:\\DB\\mpm\\file.jpg"
    python edit_efu_metadata.py --field Title --value "Barcelona" --dry-run "G:\\DB\\misc\\Chair.jpg"

Friendly field aliases (case-insensitive):
    rating                    -> Rating
    subject                   -> Subject
    title, model              -> Title
    company, brand            -> Company
    author, vendor            -> Author
    album, collection         -> Album
    tags                      -> Tags
    comment, notes            -> Comment
    period, style             -> Period
    color                     -> custom_property_0
    location                  -> custom_property_1
    form, shape               -> custom_property_2
    chinesename, chinese       -> custom_property_3
    latinname, latin           -> custom_property_4
    size, dimensions           -> custom_property_5
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

# Friendly name -> canonical EFU column name
FIELD_ALIASES: dict[str, str] = {
    "rating":       "Rating",
    "subject":      "Subject",
    "title":        "Title",
    "model":        "Title",
    "company":      "Company",
    "brand":        "Company",
    "author":       "Author",
    "vendor":       "Author",
    "album":        "Album",
    "collection":   "Album",
    "tags":         "Tags",
    "comment":      "Comment",
    "notes":        "Comment",
    "period":       "Period",
    "style":        "Period",
    "color":        "custom_property_0",
    "colour":       "custom_property_0",
    "location":     "custom_property_1",
    "form":         "custom_property_2",
    "shape":        "custom_property_2",
    "chinesename":  "custom_property_3",
    "chinese":      "custom_property_3",
    "latinname":    "custom_property_4",
    "latin":        "custom_property_4",
    "size":         "custom_property_5",
    "dimensions":   "custom_property_5",
}

VALID_RATINGS = {1, 25, 50, 75, 99}


def resolve_field(field: str) -> str:
    """Resolve a friendly name or raw column name to the canonical EFU column name."""
    lower = field.lower().replace(" ", "").replace("_", "")
    # Try alias map (strip underscores/spaces for fuzzy match)
    for alias, col in FIELD_ALIASES.items():
        if lower == alias.replace("_", ""):
            return col
    # Try exact match as-is (handles custom_property_0 etc. directly)
    return field


def _load_efu(efu_path: Path) -> tuple[list[str], list[dict]]:
    """Load EFU CSV, return (fieldnames, rows)."""
    with efu_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    return fieldnames, rows


def _write_efu(efu_path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """Write rows back to the EFU file using atomic replace."""
    tmp = efu_path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore",
                                quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(efu_path)


def _row_basename(row: dict) -> str:
    """Extract the basename from a row's Filename, lowercased."""
    fn = row.get("Filename", "").strip().strip('"')
    return Path(fn).name.lower()


def update_efu(
    efu_path: Path,
    target_basenames: set[str],
    column: str,
    value: str,
    dry_run: bool,
) -> int:
    """Update a column for matching rows. Returns count of updated rows."""
    if not efu_path.exists():
        print(f"  [error] EFU not found: {efu_path}")
        return 0

    fieldnames, rows = _load_efu(efu_path)

    if "Filename" not in fieldnames:
        print(f"  [error] No Filename column in {efu_path}")
        return 0

    # Add column to fieldnames if missing
    if column not in fieldnames:
        fieldnames.append(column)
        print(f"  [info] Column '{column}' not in EFU — will be added.")

    updated = 0
    not_found = set(target_basenames)

    for row in rows:
        bn = _row_basename(row)
        if bn in target_basenames:
            old = row.get(column, "-")
            if not dry_run:
                row[column] = value
            prefix = "[DRY RUN] " if dry_run else ""
            fn = Path(row.get("Filename", "").strip().strip('"')).name
            print(f"  {prefix}{fn}: {column} {old!r} -> {value!r}")
            updated += 1
            not_found.discard(bn)

    if not_found:
        print(f"  [warn] Not found in EFU: {', '.join(sorted(not_found))}")

    if updated == 0:
        return 0

    if not dry_run:
        _write_efu(efu_path, fieldnames, rows)
        print(f"  -> Wrote {updated} change(s) to {efu_path}")
    else:
        print(f"  -> DRY RUN: would update {updated} row(s) in {efu_path}")

    return updated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update any field in .metadata.efu for specified asset files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--field", required=True,
                        help="EFU column or friendly alias (e.g. rating, subject, title, color).")
    parser.add_argument("--value", required=True,
                        help="New value to set.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing.")
    parser.add_argument("files", nargs="+",
                        help="Full paths to asset files to update.")
    args = parser.parse_args()

    column = resolve_field(args.field)
    value = args.value

    # Warn if rating value is non-standard
    if column == "Rating":
        try:
            if int(value) not in VALID_RATINGS:
                print(f"[warn] {value} is not a standard rating. Standard: {sorted(VALID_RATINGS)}")
        except ValueError:
            print(f"[error] Rating must be an integer, got: {value!r}")
            sys.exit(1)

    print(f"Field: {column}  |  Value: {value!r}  |  Dry-run: {args.dry_run}")

    # Group files by directory — each dir has its own .metadata.efu
    by_dir: dict[Path, list[Path]] = defaultdict(list)
    for f in args.files:
        p = Path(f)
        by_dir[p.parent].append(p)

    total_updated = 0

    for directory, file_list in by_dir.items():
        target_basenames = {p.name.lower() for p in file_list}
        efu_path = directory / ".metadata.efu"

        print(f"\nDirectory : {directory}")
        print(f"EFU       : {efu_path}")

        n = update_efu(efu_path, target_basenames, column, value, args.dry_run)
        total_updated += n

    print(f"\nTotal files updated: {total_updated}")
    sys.exit(0)


if __name__ == "__main__":
    main()
