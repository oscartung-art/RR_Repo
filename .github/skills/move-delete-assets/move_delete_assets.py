#!/usr/bin/env python3
"""
move_delete_assets.py — Move or delete assets and keep .metadata.efu in sync.

MOVE: moves thumbnail + matching archive to destination, updates Album to dest
      folder name, rewrites Filename in both source and dest EFU files.
DELETE: removes EFU rows only — does NOT delete the actual files
        (user handles file deletion manually).

Both modes also update D:\\RR_Repo\\Database\\.metadata.efu (central index with
full-path Filename values) when a matching row is found there.

Usage:
    python move_delete_assets.py --move "G:\\DB\\dest\\" FILE [FILE ...]
    python move_delete_assets.py --delete FILE [FILE ...]
    python move_delete_assets.py --move "G:\\DB\\dest\\" --dry-run FILE [FILE ...]
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
from collections import defaultdict
from pathlib import Path

# Central index that stores full-path Filename values.
CENTRAL_EFU = Path(r"D:\rr_repo\Database\.metadata.efu")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
ARCHIVE_EXTENSIONS = {".zip", ".rar", ".7z"}
MODEL_EXTENSIONS = {
    ".abc", ".blend", ".c4d", ".dae", ".fbx", ".glb", ".gltf", ".ifc",
    ".ma", ".max", ".mb", ".obj", ".ply", ".skp", ".stl", ".usd",
    ".usda", ".usdc", ".usdz", ".3ds",
}
ASSET_EXTENSIONS = ARCHIVE_EXTENSIONS | MODEL_EXTENSIONS


# ---------------------------------------------------------------------------
# EFU I/O helpers
# ---------------------------------------------------------------------------

def _load_efu(path: Path) -> tuple[list[str], list[dict]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    return fieldnames, rows


def _write_efu(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames,
                                extrasaction="ignore", quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _row_basename(row: dict) -> str:
    fn = row.get("Filename", "").strip().strip('"')
    return Path(fn).name.lower()


def _uses_full_paths(rows: list[dict]) -> bool:
    """Return True if EFU Filename values look like absolute paths."""
    for row in rows[:5]:
        fn = row.get("Filename", "").strip().strip('"')
        if fn and Path(fn).is_absolute():
            return True
    return False


# ---------------------------------------------------------------------------
# Archive discovery
# ---------------------------------------------------------------------------

def _find_archive(image_path: Path, efu_row: dict | None) -> Path | None:
    """Find the matching archive for an image.

    Checks: 1) ArchiveFile column in EFU row, 2) same stem in same folder.
    """
    if efu_row:
        archive_name = (efu_row.get("ArchiveFile") or "").strip().strip('"')
        if archive_name and archive_name != "-":
            candidate = image_path.parent / archive_name
            if candidate.exists():
                return candidate

    stem = image_path.stem
    for ext in ASSET_EXTENSIONS:
        candidate = image_path.parent / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


# ---------------------------------------------------------------------------
# EFU update operations
# ---------------------------------------------------------------------------

def _remove_from_efu(
    efu_path: Path,
    basenames: set[str],
    dry_run: bool,
) -> list[dict]:
    """Remove rows matching basenames from efu_path. Returns removed rows."""
    if not efu_path.exists():
        return []
    fieldnames, rows = _load_efu(efu_path)
    kept, removed = [], []
    for row in rows:
        if _row_basename(row) in basenames:
            removed.append(row)
        else:
            kept.append(row)
    if removed and not dry_run:
        _write_efu(efu_path, fieldnames, kept)
    return removed


def _remove_from_central_efu(
    full_paths: list[Path],
    dry_run: bool,
) -> list[dict]:
    """Remove rows from the central Database EFU by full-path match."""
    if not CENTRAL_EFU.exists():
        return []
    fieldnames, rows = _load_efu(CENTRAL_EFU)
    target_paths = {str(p).lower() for p in full_paths}
    kept, removed = [], []
    for row in rows:
        fn = row.get("Filename", "").strip().strip('"').lower()
        if fn in target_paths:
            removed.append(row)
        else:
            kept.append(row)
    if removed and not dry_run:
        _write_efu(CENTRAL_EFU, fieldnames, kept)
    return removed


def _add_to_efu(
    efu_path: Path,
    new_rows: list[dict],
    dry_run: bool,
    use_full_paths: bool,
    dest_dir: Path,
    album_value: str,
) -> None:
    """Append new_rows to efu_path, updating Filename and Album."""
    if not new_rows:
        return

    if efu_path.exists():
        fieldnames, existing_rows = _load_efu(efu_path)
    else:
        # Seed fieldnames from first row
        fieldnames = list(new_rows[0].keys())
        existing_rows = []

    # Ensure Album is in fieldnames
    if "Album" not in fieldnames:
        fieldnames.append("Album")

    updated_rows = []
    for row in new_rows:
        r = dict(row)
        orig_name = Path(r.get("Filename", "").strip().strip('"')).name
        if use_full_paths:
            r["Filename"] = str(dest_dir / orig_name)
        else:
            r["Filename"] = orig_name
        r["Album"] = album_value
        updated_rows.append(r)
        prefix = "[DRY RUN] " if dry_run else ""
        print(f"  {prefix}+ {orig_name}  Album={album_value!r}")

    if not dry_run:
        _write_efu(efu_path, fieldnames, existing_rows + updated_rows)
        print(f"  -> Wrote {len(updated_rows)} row(s) to {efu_path}")
    else:
        print(f"  -> DRY RUN: would add {len(updated_rows)} row(s) to {efu_path}")


def _update_central_efu_move(
    removed_rows: list[dict],
    dest_dir: Path,
    album_value: str,
    dry_run: bool,
) -> None:
    """In the central EFU, update Filename path and Album for moved rows."""
    if not removed_rows or not CENTRAL_EFU.exists():
        return
    fieldnames, rows = _load_efu(CENTRAL_EFU)
    if "Album" not in fieldnames:
        fieldnames.append("Album")

    updated_count = 0
    for row in rows:
        fn = row.get("Filename", "").strip().strip('"')
        basename = Path(fn).name
        for r in removed_rows:
            orig = Path(r.get("Filename", "").strip().strip('"')).name
            if orig.lower() == basename.lower():
                new_path = str(dest_dir / basename)
                if not dry_run:
                    row["Filename"] = new_path
                    row["Album"] = album_value
                else:
                    print(f"  [DRY RUN] central EFU: {fn!r} -> {new_path!r}  Album={album_value!r}")
                updated_count += 1

    if updated_count and not dry_run:
        _write_efu(CENTRAL_EFU, fieldnames, rows)
        print(f"  -> Updated {updated_count} row(s) in central EFU: {CENTRAL_EFU}")


# ---------------------------------------------------------------------------
# Move logic
# ---------------------------------------------------------------------------

def do_move(
    image_paths: list[Path],
    dest_dir: Path,
    dry_run: bool,
) -> None:
    dest_dir = dest_dir.resolve()
    album_value = dest_dir.name

    # Group by source directory
    by_src: dict[Path, list[Path]] = defaultdict(list)
    for p in image_paths:
        by_src[p.parent.resolve()].append(p)

    for src_dir, imgs in by_src.items():
        src_efu = src_dir / ".metadata.efu"
        dest_efu = dest_dir / ".metadata.efu"

        print(f"\nSource : {src_dir}")
        print(f"Dest   : {dest_dir}")

        # Load source EFU to get rows and detect format
        if src_efu.exists():
            src_fieldnames, src_rows = _load_efu(src_efu)
            src_full = _uses_full_paths(src_rows)
            row_by_basename = {_row_basename(r): r for r in src_rows}
        else:
            print(f"  [warn] No EFU at source: {src_efu}")
            src_full = False
            row_by_basename = {}

        # Detect dest EFU format
        dest_full = False
        if dest_efu.exists():
            _, dest_rows_existing = _load_efu(dest_efu)
            dest_full = _uses_full_paths(dest_rows_existing)
        elif src_full:
            dest_full = True

        basenames_to_remove: set[str] = set()
        rows_to_add: list[dict] = []

        for img in imgs:
            bn = img.name.lower()
            efu_row = row_by_basename.get(bn)

            # Find archive
            archive = _find_archive(img, efu_row)
            archive_dest = dest_dir / archive.name if archive else None

            prefix = "[DRY RUN] " if dry_run else ""
            print(f"  {prefix}MOVE {img.name}")
            if archive:
                print(f"         + {archive.name}")
            else:
                print(f"         (no archive found)")

            # Move files
            if not dry_run:
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(img), str(dest_dir / img.name))
                if archive:
                    shutil.move(str(archive), str(archive_dest))

            basenames_to_remove.add(bn)
            if efu_row:
                r = dict(efu_row)
                # Normalise Filename to basename for portability
                r["Filename"] = img.name
                if archive:
                    r["ArchiveFile"] = archive.name
                rows_to_add.append(r)

        # Remove from source EFU
        removed = []
        if src_efu.exists():
            removed = _remove_from_efu(src_efu, basenames_to_remove, dry_run)
            prefix = "[DRY RUN] " if dry_run else ""
            print(f"  {prefix}Removed {len(removed)} row(s) from {src_efu}")

        # Add to dest EFU
        _add_to_efu(dest_efu, rows_to_add, dry_run, dest_full, dest_dir, album_value)

        # Update central EFU
        central_removed = _remove_from_central_efu([img.resolve() for img in imgs], dry_run)
        if central_removed:
            prefix = "[DRY RUN] " if dry_run else ""
            print(f"  {prefix}Removed {len(central_removed)} row(s) from central EFU")
        _update_central_efu_move(removed, dest_dir, album_value, dry_run)


# ---------------------------------------------------------------------------
# Delete logic
# ---------------------------------------------------------------------------

def do_delete(
    image_paths: list[Path],
    dry_run: bool,
) -> None:
    by_src: dict[Path, list[Path]] = defaultdict(list)
    for p in image_paths:
        by_src[p.parent.resolve()].append(p)

    total_removed = 0
    for src_dir, imgs in by_src.items():
        efu_path = src_dir / ".metadata.efu"
        basenames = {p.name.lower() for p in imgs}

        print(f"\nDirectory : {src_dir}")
        removed = _remove_from_efu(efu_path, basenames, dry_run)
        prefix = "[DRY RUN] " if dry_run else ""
        for r in removed:
            fn = Path(r.get("Filename", "")).name
            print(f"  {prefix}- {fn}")
        if not dry_run and removed:
            print(f"  -> Removed {len(removed)} row(s) from {efu_path}")
        elif dry_run and removed:
            print(f"  -> DRY RUN: would remove {len(removed)} row(s) from {efu_path}")
        else:
            print(f"  [warn] No matching rows found in {efu_path}")
        total_removed += len(removed)

    # Central EFU
    central_removed = _remove_from_central_efu(
        [p.resolve() for p in image_paths], dry_run
    )
    if central_removed:
        prefix = "[DRY RUN] " if dry_run else ""
        print(f"\n{prefix}Removed {len(central_removed)} row(s) from central EFU: {CENTRAL_EFU}")
    total_removed += len(central_removed)

    print(f"\nTotal rows removed: {total_removed}")
    print("Note: actual files were NOT deleted — remove them manually.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Move or delete assets and keep .metadata.efu in sync.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--move", metavar="DEST_DIR",
                      help="Destination folder to move assets into.")
    mode.add_argument("--delete", action="store_true",
                      help="Remove EFU entries only (no file deletion).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing or moving.")
    parser.add_argument("files", nargs="+",
                        help="Full paths to thumbnail image files.")
    args = parser.parse_args()

    image_paths = [Path(f).resolve() for f in args.files]
    missing = [p for p in image_paths if not p.exists() and not args.dry_run]
    if missing:
        for m in missing:
            print(f"[error] File not found: {m}")
        sys.exit(1)

    if args.move:
        dest = Path(args.move)
        print(f"Mode: MOVE -> {dest}  |  Dry-run: {args.dry_run}")
        do_move(image_paths, dest, args.dry_run)
    else:
        print(f"Mode: DELETE (EFU only)  |  Dry-run: {args.dry_run}")
        do_delete(image_paths, args.dry_run)


if __name__ == "__main__":
    main()
