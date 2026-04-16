"""migrate_thumbnails_to_gdb.py

One-off script to:
  1. Move all thumbnail .jpg/.jpeg files from D:/RR_Repo/Database/ to G:/DB/
  2. Update Filename in Database/.metadata.efu to absolute G:\\DB\\<name> paths.

Usage:
    python tools/migrate_thumbnails_to_gdb.py [--dry-run]
"""
from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

SOURCE_DIR = Path(r"D:\RR_Repo\Database")
DEST_DIR = Path(r"G:\DB")
METADATA_EFU_PATH = SOURCE_DIR / ".metadata.efu"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

EFU_HEADERS = [
    "Filename", "Subject", "Rating", "Tags", "URL", "Company", "Author",
    "Album", "custom_property_0", "custom_property_1", "custom_property_2",
    "Period", "Title", "Comment", "ArchiveFile", "SourceMetadata",
    "Content Status", "custom_property_3", "custom_property_4",
    "custom_property_5", "CRC-32",
]


def read_efu(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        headers = reader.fieldnames or EFU_HEADERS
        rows = [dict(row) for row in reader]
    return list(headers), rows


def write_efu(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "-") or "-" for k in headers})


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("[DRY-RUN] No files will be moved and no EFU will be written.\n")

    if not METADATA_EFU_PATH.exists():
        print(f"ERROR: EFU not found at {METADATA_EFU_PATH}")
        sys.exit(1)

    DEST_DIR.mkdir(parents=True, exist_ok=True)

    headers, rows = read_efu(METADATA_EFU_PATH)

    moved = 0
    already_there = 0
    skipped_not_found = 0
    efu_updated = 0

    for row in rows:
        stored = (row.get("Filename") or "").strip()
        if not stored or stored == "-":
            continue

        stored_path = Path(stored)

        # Already absolute and pointing to G:\DB — nothing to do for this row.
        if stored_path.is_absolute() and stored_path.drive.upper() == DEST_DIR.drive.upper():
            continue

        # Derive the bare filename (handles both bare names and old absolute paths).
        basename = stored_path.name
        if not basename or basename == "-":
            continue

        # Only process image files (archives stay in G:\DB as-is).
        if stored_path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        dest_path = DEST_DIR / basename
        new_filename = str(dest_path)

        # Determine source for the move.
        if stored_path.is_absolute():
            src_path = stored_path
        else:
            src_path = SOURCE_DIR / basename

        if dest_path.exists():
            already_there += 1
            print(f"  [skip-move] already at dest: {dest_path.name}")
        elif src_path.exists():
            if not dry_run:
                shutil.move(str(src_path), str(dest_path))
            print(f"  [move] {src_path} -> {dest_path}")
            moved += 1
        else:
            skipped_not_found += 1
            print(f"  [warn] source not found, EFU updated anyway: {src_path}")

        # Update Filename in the row regardless of whether we moved (dest may already exist).
        row["Filename"] = new_filename
        efu_updated += 1

    print()
    print(f"Files moved:           {moved}")
    print(f"Already at dest:       {already_there}")
    print(f"Source not found:      {skipped_not_found}")
    print(f"EFU rows updated:      {efu_updated}")

    if not dry_run:
        write_efu(METADATA_EFU_PATH, headers, rows)
        print(f"\nEFU written: {METADATA_EFU_PATH}")
    else:
        print("\n(dry-run) EFU not written.")


if __name__ == "__main__":
    main()
