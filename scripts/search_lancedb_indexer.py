"""
search_lancedb_indexer.py — Gradual LanceDB Asset Indexer

Prompts for a target folder or file list each run so indexing is always
deliberate and incremental rather than a full crawl.

Schema:  relative_filepath (str) | qwen_description (str) | vector (embedding)

Paths stored in LanceDB are ALWAYS relative to the database root so the
Everything Search / .efu workflow stays portable across machines.

Install:
    pip install lancedb[embeddings] sentence-transformers Pillow

Usage:
    # Interactive prompt for database root and scan target:
    python scripts/search_lancedb_indexer.py

    # Non-interactive with explicit root:
    python scripts/search_lancedb_indexer.py --db-root "D:/GoogleDrive/Database"

    # Or via environment variable:
    set DATABASE_ROOT=D:/GoogleDrive/Database
    python scripts/search_lancedb_indexer.py
"""

import argparse
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
WORKSPACE_ROOT  = Path(__file__).resolve().parents[1]
LANCEDB_URI     = WORKSPACE_ROOT / "db" / "assets.lancedb"
LANCE_TABLE     = os.environ.get("RR_LANCE_TABLE", "assets")
EMBEDDING_MODEL = os.environ.get("RR_EMBED_MODEL", "Alibaba-NLP/gte-Qwen2-1.5B-instruct")
EMBEDDING_DEVICE = os.environ.get("RR_EMBED_DEVICE", "cuda")
BATCH_SIZE      = 32

IMAGE_EXTS = frozenset({
    ".jpg", ".jpeg", ".png", ".tga", ".bmp", ".tiff",
    ".exr", ".hdr", ".gif", ".webp",
})

# ---------------------------------------------------------------------------
# MOCK Qwen-VL DESCRIBER
# Swap this function body for real Qwen-VL inference when the model is ready.
# Contract: accept a Path, return a descriptive string.
# ---------------------------------------------------------------------------
def mock_qwen_describe(image_path):
    """
    Returns a descriptive text string for the given image.
    Currently mocked — replace with real Qwen-VL inference.
    """
    stem   = image_path.stem.replace("_", " ").replace("-", " ")
    parent = image_path.parent.name.replace("_", " ")
    return f"A 3D asset image showing {stem}, located in the {parent} category."

# ---------------------------------------------------------------------------
# DATABASE ROOT RESOLUTION
# ---------------------------------------------------------------------------
def _resolve_db_root(cli_arg):
    """Resolve the database root from CLI arg, env var, or interactive prompt."""
    candidate = cli_arg or os.environ.get("DATABASE_ROOT", "")
    if candidate:
        p = Path(candidate)
        if p.exists() and p.is_dir():
            return p.resolve()
        print(f"[indexer] WARNING: path not found or not a directory: {p}")

    while True:
        raw = input("[indexer] Enter database root folder (images root): ").strip().strip('"')
        if not raw:
            continue
        p = Path(raw)
        if p.exists() and p.is_dir():
            return p.resolve()
        print(f"  Path not found or not a directory: {p}")

# ---------------------------------------------------------------------------
# SCAN TARGET SELECTION
# ---------------------------------------------------------------------------
def _choose_scan_targets(db_root):
    """
    Prompt for which subfolder(s) or file(s) to index this run.
    Returns a list of resolved absolute Paths.
    """
    print(f"\n[indexer] Database root: {db_root}")
    print("[indexer] Enter subfolder(s) or file(s) to scan this run.")
    print("          Path can be relative to the database root, or absolute.")
    print("          Separate multiple targets with a semicolon  ';'.")
    print("          Press Enter alone to scan the entire database root.\n")
    raw = input("Scan target(s): ").strip()

    if not raw:
        return [db_root]

    targets = []
    for part in raw.split(";"):
        part = part.strip().strip('"')
        if not part:
            continue
        p = Path(part)
        if not p.is_absolute():
            p = db_root / p
        p = p.resolve()
        if p.exists():
            targets.append(p)
        else:
            print(f"  [indexer] Skipping (not found): {p}")

    return targets or [db_root]

# ---------------------------------------------------------------------------
# FILE COLLECTION
# ---------------------------------------------------------------------------
def _collect_images(targets):
    """Recursively collect all image files under the given targets, deduplicated."""
    seen    = set()
    deduped = []
    for target in targets:
        candidates = []
        if target.is_file():
            candidates = [target]
        elif target.is_dir():
            for ext in IMAGE_EXTS:
                candidates.extend(target.rglob(f"*{ext}"))
                candidates.extend(target.rglob(f"*{ext.upper()}"))
        for p in candidates:
            if p.suffix.lower() in IMAGE_EXTS:
                key = p.resolve()
                if key not in seen:
                    seen.add(key)
                    deduped.append(p)
    return deduped

# ---------------------------------------------------------------------------
# LANCEDB CONNECTION + SCHEMA
# ---------------------------------------------------------------------------
def _connect_lancedb(embedding_fn):
    import lancedb
    from lancedb.pydantic import LanceModel, Vector

    db = lancedb.connect(str(LANCEDB_URI))

    class AssetRecord(LanceModel):
        relative_filepath: str
        qwen_description: str           = embedding_fn.SourceField()
        vector: Vector(embedding_fn.ndims()) = embedding_fn.VectorField()

    if LANCE_TABLE in db.table_names():
        tbl = db.open_table(LANCE_TABLE)
        print(f"[indexer] Opened existing table '{LANCE_TABLE}'.")
    else:
        tbl = db.create_table(LANCE_TABLE, schema=AssetRecord)
        print(f"[indexer] Created new table '{LANCE_TABLE}'.")

    return tbl

# ---------------------------------------------------------------------------
# UPSERT HELPER
# ---------------------------------------------------------------------------
def _upsert_batch(tbl, batch):
    (
        tbl.merge_insert("relative_filepath")
           .when_matched_update_all()
           .when_not_matched_insert_all()
           .execute(batch)
    )

# ---------------------------------------------------------------------------
# MAIN INDEXING LOGIC
# ---------------------------------------------------------------------------
def index(db_root, targets, embedding_model=EMBEDDING_MODEL, embedding_device=EMBEDDING_DEVICE):
    if embedding_device == "cuda":
        try:
            import torch
            if not torch.cuda.is_available():
                print("[indexer] CUDA not available. Falling back to CPU for embeddings.")
                embedding_device = "cpu"
        except Exception:
            print("[indexer] Torch unavailable for CUDA check. Falling back to CPU.")
            embedding_device = "cpu"

    print(f"\n[indexer] Loading embedding model ({embedding_model}) on {embedding_device} ...")
    try:
        from lancedb.embeddings import get_registry
    except ImportError:
        sys.exit(
            "[indexer] lancedb not installed.\n"
            "Run: pip install lancedb[embeddings] sentence-transformers"
        )

    embedding_fn = (
        get_registry()
        .get("sentence-transformers")
        .create(name=embedding_model, device=embedding_device)
    )

    tbl    = _connect_lancedb(embedding_fn)
    images = _collect_images(targets)

    if not images:
        print("[indexer] No images found in the selected targets.")
        return

    print(f"[indexer] {len(images)} images found. Upserting into '{LANCE_TABLE}' ...\n")
    inserted = 0
    skipped  = 0
    errors   = 0
    batch    = []

    for i, img_path in enumerate(images, 1):
        # Compute relative path from db_root — forward slashes for portability
        try:
            rel     = img_path.resolve().relative_to(db_root)
            rel_str = rel.as_posix()
        except ValueError:
            print(f"  SKIP (outside db_root): {img_path}")
            skipped += 1
            continue

        try:
            description = mock_qwen_describe(img_path)
            batch.append({"relative_filepath": rel_str, "qwen_description": description})
        except Exception as exc:
            print(f"  ERROR {img_path.name}: {exc}")
            errors += 1
            continue

        if len(batch) >= BATCH_SIZE:
            try:
                _upsert_batch(tbl, batch)
                inserted += len(batch)
                print(f"  Upserted {inserted}/{len(images)} ...", end="\r", flush=True)
            except Exception as exc:
                print(f"\n  Batch upsert failed: {exc}")
                errors += len(batch)
            batch.clear()

    # Flush remaining rows
    if batch:
        try:
            _upsert_batch(tbl, batch)
            inserted += len(batch)
        except Exception as exc:
            print(f"\n  Final batch upsert failed: {exc}")
            errors += len(batch)

    print(f"\n[indexer] Done.")
    print(f"  Upserted : {inserted}")
    print(f"  Skipped  : {skipped}")
    print(f"  Errors   : {errors}")
    print(f"  Table    : {LANCE_TABLE}")
    print(f"  LanceDB  : {LANCEDB_URI}")

# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Gradual LanceDB asset indexer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python search_lancedb_indexer.py\n"
            "  python search_lancedb_indexer.py --db-root D:/GoogleDrive/Database\n"
        ),
    )
    parser.add_argument(
        "--db-root",
        default=None,
        help="Root folder of the image database. Also settable via DATABASE_ROOT env var.",
    )
    parser.add_argument(
        "--embed-model",
        default=EMBEDDING_MODEL,
        help=(
            "Text embedding model id (default: Alibaba-NLP/gte-Qwen2-1.5B-instruct). "
            "Override via RR_EMBED_MODEL."
        ),
    )
    parser.add_argument(
        "--embed-device",
        default=EMBEDDING_DEVICE,
        choices=["cuda", "cpu"],
        help="Embedding runtime device. Override via RR_EMBED_DEVICE.",
    )
    args    = parser.parse_args()
    db_root = _resolve_db_root(args.db_root)
    targets = _choose_scan_targets(db_root)
    index(db_root, targets, embedding_model=args.embed_model, embedding_device=args.embed_device)


if __name__ == "__main__":
    main()
