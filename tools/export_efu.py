"""
export_efu.py — Generate .metadata.efu from the LanceDB vector database.

Reads all records from the vector DB (source of truth) and projects them into
a .metadata.efu CSV with user-selected columns.  Add or remove columns freely;
the underlying data is always preserved in the vector DB.

Usage:
    # Export with default columns
    python tools/export_efu.py

    # Export with specific columns
    python tools/export_efu.py --columns Subject,Title,Company,Author,Color,Form

    # Export without a column (e.g. drop Color)
    python tools/export_efu.py --columns Subject,Title,Company,Author,Form

    # Preview without writing
    python tools/export_efu.py --dry-run

    # Export to a custom path
    python tools/export_efu.py --output "D:\\RR_Repo\\Database\\custom.efu"

    # List available columns from the vector DB
    python tools/export_efu.py --list-columns
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths & config
# ---------------------------------------------------------------------------
WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
LANCEDB_URI = WORKSPACE_ROOT / "db" / "assets.lancedb"
LANCE_TABLE = os.environ.get("RR_LANCE_TABLE", "assets_metadata")
METADATA_EFU_PATH = WORKSPACE_ROOT / "Database" / ".metadata.efu"
THUMBNAIL_BASE = Path(os.environ.get("INGEST_THUMBNAIL_BASE", r"G:\DB"))

# ---------------------------------------------------------------------------
# Column mapping: vector DB field → EFU header name
#
# The EFU uses Everything Search custom property names.
# This mapping lets the user think in friendly names while the EFU file
# uses the canonical column headers.
# New schema: all enrichment categories stored in custom_property 0-9
# ---------------------------------------------------------------------------
FIELD_TO_EFU = {
    "filepath":        "Filename",
    "subject":         "custom_property_0",
    "brand":           "custom_property_2",
    "author":          "custom_property_4",
    "album":           "custom_property_3",
    "color":           "custom_property_4",
    "usage_location":  "custom_property_5",
    "shape_form":      "custom_property_6",
    "period":          "custom_property_3",
    "model_name":      "custom_property_1",
    "archive_file":    "ArchiveFile",
    "crc32":           "CRC-32",
    "size":            "custom_property_7",
    "sidecar_text":    "SourceMetadata",
    "vendor_name":     "custom_property_4",  # fallback
    "collection":      "custom_property_3",  # fallback
    "description":     "Comment",
}

# Friendly name aliases so users can type --columns Color instead of custom_property_4
FRIENDLY_NAMES = {
    # New schema: friendly name → canonical custom_property slot
    "subject":      "custom_property_0",
    "title":        "custom_property_1",
    "model":        "custom_property_1",
    "company":      "custom_property_2",
    "brand":        "custom_property_2",
    "album":        "custom_property_3",
    "collection":  "custom_property_3",
    "author":       "custom_property_4",
    "color":        "custom_property_4",
    "finish":       "custom_property_4",
    "period":       "custom_property_5",
    "location":     "custom_property_5",
    "form":         "custom_property_6",
    "shape":        "custom_property_6",
    "size":         "custom_property_7",
    "dimensions":   "custom_property_7",
    "code":         "custom_property_8",
    "refcode":      "custom_property_8",
    "archive":      "ArchiveFile",
    "crc":          "CRC-32",
    "crc32":        "CRC-32",
    "crc-32":       "CRC-32",
    "comment":      "Comment",
    "description":  "Comment",
    "source":       "SourceMetadata",
    "sidecar":      "SourceMetadata",
}

# Default EFU columns — matches the canonical schema
DEFAULT_EFU_COLUMNS = [
    "Filename",
    "Rating",
    "Tags",
    "URL",
    "Comment",
    "ArchiveFile",
    "SourceMetadata",
    "Content Status",
    "CRC-32",
    "custom_property_0",   # Subject (Primary asset classification)
    "custom_property_1",   # Title (Model name/designer name)
    "custom_property_2",   # Company (Brand/Designer/Collection identifier)
    "custom_property_3",   # Album (Style or era classification)
    "custom_property_4",   # Author (Primary color/material/surface finish)
    "custom_property_5",   # Period (Usage context/location)
    "custom_property_6",   # Color (Shape/physical configuration)
    "custom_property_7",   # Location (Dimensions/scale classification)
    "custom_property_8",   # Form (Reference code)
    "custom_property_9",   # Size (reserved/unused)
]

# Which vector DB field populates which EFU column
DB_FIELD_FOR_EFU_COL = {
    "Filename":         "filepath",
    "Rating":           "rating",
    "Tags":             "tags",
    "URL":              "url",
    "Comment":          "description",
    "ArchiveFile":      "archive_file",
    "SourceMetadata":   "sidecar_text",
    "Content Status":   "content_status",
    "CRC-32":           "crc32",
    "custom_property_0": "subject",
    "custom_property_1": "model_name",
    "custom_property_2": "brand",
    "custom_property_3": "period",
    "custom_property_4": "color",
    "custom_property_5": "usage_location",
    "custom_property_6": "shape_form",
    "custom_property_7": "size",
    "custom_property_8": "code",
    "custom_property_9": "-",
}


def _resolve_columns(user_cols: str | None) -> list[str]:
    """Resolve user-specified column names to canonical EFU header names.

    If user_cols is None, returns DEFAULT_EFU_COLUMNS.
    User can use friendly names like 'Color', 'Form', 'Title' or
    canonical names like 'custom_property_0'.
    """
    if not user_cols:
        return list(DEFAULT_EFU_COLUMNS)

    parts = [c.strip() for c in user_cols.split(",") if c.strip()]
    resolved: list[str] = []

    # Always include Filename as the first column
    if "Filename" not in resolved:
        resolved.append("Filename")

    for part in parts:
        lower = part.lower()
        if lower == "filename":
            continue  # already added
        # Check friendly name mapping
        if lower in FRIENDLY_NAMES:
            efu_name = FRIENDLY_NAMES[lower]
            if efu_name not in resolved:
                resolved.append(efu_name)
        # Check if it's already a valid EFU column name
        elif part in DEFAULT_EFU_COLUMNS:
            if part not in resolved:
                resolved.append(part)
        else:
            print(f"[export] WARNING: Unknown column '{part}', skipping.")

    # Always include CRC-32 at the end
    if "CRC-32" not in resolved:
        resolved.append("CRC-32")

    return resolved


def _record_to_efu_row(record: dict, columns: list[str]) -> dict[str, str]:
    """Map a vector DB record to an EFU row dict with the requested columns."""
    row: dict[str, str] = {}

    for col in columns:
        db_field = DB_FIELD_FOR_EFU_COL.get(col, "")
        if db_field:
            value = str(record.get(db_field, "-")).strip()
            if col == "Filename":
                # Convert relative posix path back to Windows absolute path
                if not value.startswith(("G:", "D:", "E:", "F:")):
                    value = str(THUMBNAIL_BASE / value.replace("/", os.sep))
                value = value.replace("/", "\\")
            row[col] = value if value else "-"
        else:
            row[col] = "-"

    return row


def _load_records_from_db():
    """Load all records from the LanceDB table."""
    try:
        import lancedb
    except ImportError:
        sys.exit("[export] lancedb not installed. Run: pip install lancedb[embeddings]")

    db = lancedb.connect(str(LANCEDB_URI))
    table_list = db.list_tables() if hasattr(db, 'list_tables') else db.table_names()
    if LANCE_TABLE not in table_list:
        print(f"[export] Table '{LANCE_TABLE}' not found in {LANCEDB_URI}")
        print("[export] Run ingest_to_vectordb.py first to populate the database.")
        sys.exit(1)

    tbl = db.open_table(LANCE_TABLE)
    df = tbl.to_pandas()
    print(f"[export] Loaded {len(df)} records from '{LANCE_TABLE}'.")

    records = []
    for _, row in df.iterrows():
        rec = {k: str(v) if v is not None else "" for k, v in row.items()
               if k != "vector"}
        records.append(rec)
    return records, list(df.columns)


def _list_available_columns(db_columns: list[str]) -> None:
    """Print available vector DB fields and their friendly names."""
    print("\nAvailable fields in vector DB:")
    print(f"{'DB Field':<20} {'EFU Column':<20} {'Friendly Name':<15}")
    print("-" * 55)
    for field, efu_col in sorted(DB_FIELD_FOR_EFU_COL.items(), key=lambda x: x[0]):
        db_field = DB_FIELD_FOR_EFU_COL.get(efu_col, efu_col)
        # Find friendly name
        friendly = ""
        for fname, ecol in FRIENDLY_NAMES.items():
            if ecol == efu_col:
                friendly = fname
                break
        # Find the reverse: which DB field
        source = ""
        for col, dbf in DB_FIELD_FOR_EFU_COL.items():
            if col == efu_col:
                source = dbf
                break
        print(f"  {source or '-':<20} {efu_col:<20} {friendly:<15}")

    print(f"\nAll DB columns: {', '.join(c for c in db_columns if c != 'vector')}")


def main():
    parser = argparse.ArgumentParser(
        description="Export .metadata.efu from the LanceDB vector database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Column examples:\n"
            "  --columns Subject,Title,Company,Author,Color,Form,Size\n"
            "  --columns Subject,Title,Author    (minimal EFU)\n"
            "\nFriendly names: Color, Location, Form, Size, Title, Subject,\n"
            "  Company, Brand, Author, Album, Period, Archive, CRC, Comment\n"
        ),
    )
    parser.add_argument(
        "--columns", default=None,
        help="Comma-separated list of columns to include (default: full schema).",
    )
    parser.add_argument(
        "--output", default=None,
        help=f"Output EFU file path (default: {METADATA_EFU_PATH}).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview output without writing.",
    )
    parser.add_argument(
        "--list-columns", action="store_true",
        help="List available columns and exit.",
    )
    args = parser.parse_args()

    # Load from vector DB
    records, db_columns = _load_records_from_db()

    if args.list_columns:
        _list_available_columns(db_columns)
        return

    # Resolve columns
    columns = _resolve_columns(args.columns)
    print(f"[export] EFU columns: {', '.join(columns)}")

    # Convert records to EFU rows
    efu_rows: list[dict[str, str]] = []
    for rec in records:
        row = _record_to_efu_row(rec, columns)
        efu_rows.append(row)

    if args.dry_run:
        print(f"\n--- DRY RUN ({len(efu_rows)} rows) ---\n")
        # Show header
        print(",".join(columns))
        # Show first 10 rows
        for row in efu_rows[:10]:
            vals = [row.get(c, "-") for c in columns]
            print(",".join(vals))
        if len(efu_rows) > 10:
            print(f"... and {len(efu_rows) - 10} more rows")
        print(f"\n[export] Dry-run complete. Would write {len(efu_rows)} rows.")
        return

    # Write EFU file
    output_path = Path(args.output) if args.output else METADATA_EFU_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in efu_rows:
            writer.writerow(row)

    print(f"[export] Wrote {len(efu_rows)} rows to {output_path}")
    print(f"[export] Columns: {', '.join(columns)}")


if __name__ == "__main__":
    main()
