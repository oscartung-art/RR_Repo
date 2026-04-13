"""re_enrich.py — Re-enrich existing .metadata.efu rows using the improved pipeline.

Reads the existing .metadata.efu database, extracts the original source stem
from the Manager column (src=<stem>), and re-runs the text + web pipeline to
fill missing or stale fields.

By default only updates fields that are currently blank/dash (safe mode).
Use --force to overwrite existing values.

Fields updated by this script (text + web pipeline):
  Author  → model_name
  Writer  → brand
  Album   → collection
  People  → usage_location

Fields NOT touched (managed by enrich_visual.py):
  Genre, Company, Period

Usage:
  python tools/re_enrich.py [--dry-run] [--yes] [--force] [--limit=N] [--only-missing-brand]

Flags:
  --dry-run            Preview changes without writing
  --yes, -y            Auto-confirm without prompting
  --force              Overwrite fields even if already filled
  --limit=N            Process at most N rows
  --only-missing-brand Only process rows where Writer (brand) is '-'
"""

import csv
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ingest_asset import (
    enrich_row_with_models,
    parse_filename_hints,
    EFU_HEADERS,
    load_furniture_subcategories,
    USAGE_LOCATION_ROOMS,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
METADATA_EFU_PATH = Path(r"D:\DB\.metadata.efu")

# Fields this script is responsible for
TEXT_FIELDS = {
    "Author": "model_name",
    "Writer": "brand",
    "Album":  "collection",
    "People": "usage_location",
}


# ---------------------------------------------------------------------------
# EFU helpers
# ---------------------------------------------------------------------------
def _load_efu(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        print(f"[ERROR] EFU file not found: {path}")
        sys.exit(1)
    with path.open("r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return list(reader)


def _save_efu(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=EFU_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "-") or "-" for k in EFU_HEADERS})


def _extract_stem(manager: str) -> str:
    """Extract original source stem from Manager field (src=<stem>)."""
    m = re.search(r"src=([^;]+)", manager or "")
    if m:
        return m.group(1).strip()
    return ""


def _is_blank(value: str) -> bool:
    return not value or value.strip() in ("", "-")


def _needs_update(row: dict[str, str], force: bool, only_missing_brand: bool) -> bool:
    if only_missing_brand:
        return _is_blank(row.get("Writer", ""))
    if force:
        return True
    return any(_is_blank(row.get(efu_field, "")) for efu_field in TEXT_FIELDS)


def _is_furniture(row: dict[str, str]) -> bool:
    manager = row.get("Manager", "").strip()
    mood = row.get("Mood", "").strip()
    return "Furniture" in manager or mood.startswith("Furniture/")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def re_enrich(
    efu_path: Path = METADATA_EFU_PATH,
    dry_run: bool = False,
    auto_yes: bool = False,
    force: bool = False,
    limit: int | None = None,
    only_missing_brand: bool = False,
) -> None:
    rows = _load_efu(efu_path)

    candidates = [
        (i, row) for i, row in enumerate(rows)
        if _is_furniture(row) and _needs_update(row, force, only_missing_brand)
    ]

    if limit is not None:
        candidates = candidates[:limit]

    total = len(candidates)
    if total == 0:
        print("No rows need re-enrichment.")
        return

    mode = "FORCE" if force else ("MISSING BRAND ONLY" if only_missing_brand else "MISSING FIELDS")
    print(f"\nFound {total} furniture row(s) to re-enrich  [{mode}]")

    if dry_run:
        print("[DRY RUN] No changes will be written.\n")
        print(f"  {'Filename':<35} {'Stem':<45} {'Missing fields'}")
        print("  " + "-" * 110)
        for _, row in candidates:
            fname = row.get("Filename", "?")
            stem = _extract_stem(row.get("Manager", ""))
            missing = [f for f in TEXT_FIELDS if _is_blank(row.get(f, ""))]
            print(f"  {fname:<35} {stem:<45} {', '.join(missing) or '(force re-run)'}")
        return

    if not auto_yes:
        choice = input(f"\nRe-enrich {total} row(s)? [y/N]: ").strip().lower()
        if choice not in {"y", "yes"}:
            print("Aborted.")
            return

    updated = 0
    skipped = 0

    for idx, (row_idx, row) in enumerate(candidates, start=1):
        fname = row.get("Filename", "?")
        stem = _extract_stem(row.get("Manager", ""))

        if not stem:
            print(f"\n[{idx}/{total}] {fname}  [SKIP — no src= stem in Manager]")
            skipped += 1
            continue

        print(f"\n[{idx}/{total}] {fname}")
        print(f"  Stem: {stem}")

        hints = parse_filename_hints(stem)
        temp_row = {h: row.get(h, "-") or "-" for h in EFU_HEADERS}

        # Clear text fields so the pipeline fills them fresh (unless --force is off
        # and the field is already filled — in that case we preserve it)
        for efu_field in TEXT_FIELDS:
            if force or _is_blank(row.get(efu_field, "")):
                temp_row[efu_field] = "-"

        t0 = time.time()
        try:
            enriched = enrich_row_with_models(
                image_path=None,
                source_stem=stem,
                asset_type="furniture",
                hints=hints,
                row=temp_row,
            )
        except Exception as exc:
            print(f"  [ERROR] {exc}")
            skipped += 1
            continue

        elapsed = time.time() - t0
        changed: list[str] = []

        for efu_field, result_key in TEXT_FIELDS.items():
            new_val = (enriched.get(efu_field, "") or "").strip()
            old_val = (row.get(efu_field, "") or "").strip()
            if new_val and new_val != "-":
                if force or _is_blank(old_val):
                    if new_val != old_val:
                        rows[row_idx][efu_field] = new_val
                        changed.append(f"{efu_field}: '{old_val}' → '{new_val}'")

        # Also update URL if web pass found one
        web_url = (enriched.get("URL", "") or "").strip()
        if web_url and web_url != "-":
            rows[row_idx]["URL"] = web_url

        if changed:
            print(f"  Updated ({elapsed:.1f}s): {' | '.join(changed)}")
            updated += 1
        else:
            print(f"  No changes ({elapsed:.1f}s) — values unchanged or no improvement found.")
            skipped += 1

    _save_efu(efu_path, rows)
    print(f"\nDone. Updated: {updated} | Skipped/no-change: {skipped} | Total: {total}")
    print(f"Saved to: {efu_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parse_args() -> dict:
    args = {
        "dry_run": False,
        "auto_yes": False,
        "force": False,
        "limit": None,
        "only_missing_brand": False,
    }
    for arg in sys.argv[1:]:
        if arg in ("--dry-run", "--dryrun"):
            args["dry_run"] = True
        elif arg in ("--yes", "-y"):
            args["auto_yes"] = True
        elif arg == "--force":
            args["force"] = True
        elif arg == "--only-missing-brand":
            args["only_missing_brand"] = True
        elif arg.startswith("--limit="):
            try:
                args["limit"] = int(arg.split("=", 1)[1])
            except ValueError:
                print(f"[WARN] Invalid --limit value: {arg}")
        elif arg in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        else:
            print(f"[WARN] Unknown argument: {arg}")
    return args


if __name__ == "__main__":
    args = _parse_args()
    re_enrich(
        dry_run=args["dry_run"],
        auto_yes=args["auto_yes"],
        force=args["force"],
        limit=args["limit"],
        only_missing_brand=args["only_missing_brand"],
    )
