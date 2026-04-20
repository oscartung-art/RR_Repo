"""
ingest_to_vectordb.py — Build/update the LanceDB vector database (source of truth).

Scans thumbnail images, calls the AI vision model, collects sidecar text,
computes deterministic fields (Author from path, CRC-32, Album from structure),
and stores everything in a single LanceDB record per asset.

The vector DB is the single source of truth.  Use export_efu.py to project
selected columns into .metadata.efu on demand.

Usage:
    # Dry-run: show what would be indexed
    python tools/ingest_to_vectordb.py --dry-run "G:\\DB\\mpm\\mpmv07"

    # Index a folder for real
    python tools/ingest_to_vectordb.py "G:\\DB\\mpm\\mpmv07"

    # Index specific files
    python tools/ingest_to_vectordb.py "G:\\DB\\mpm\\mpmv07\\Chair_Example.jpg"

    # Re-index with fresh vision (overwrite existing AI descriptions)
    python tools/ingest_to_vectordb.py --force-vision "G:\\DB\\mpm\\mpmv07"
"""
from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import re
import sys
import time
import threading
import urllib.error
import urllib.request
import zlib
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths & config
# ---------------------------------------------------------------------------
WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
LANCEDB_URI = WORKSPACE_ROOT / "db" / "assets.lancedb"
LANCE_TABLE = os.environ.get("RR_LANCE_TABLE", "assets_metadata")
EMBEDDING_MODEL = os.environ.get("RR_EMBED_MODEL", "Alibaba-NLP/gte-Qwen2-1.5B-instruct")
EMBEDDING_DEVICE = os.environ.get("RR_EMBED_DEVICE", "cuda")
BATCH_SIZE = 16

THUMBNAIL_BASE = Path(os.environ.get("INGEST_THUMBNAIL_BASE", r"G:\DB"))
ARCHIVE_BASE = Path(os.environ.get("INGEST_ARCHIVE_BASE", r"G:\DB"))
METADATA_EFU_PATH = WORKSPACE_ROOT / "Database" / ".metadata.efu"

IMAGE_EXTS = frozenset({
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff",
})
ARCHIVE_EXTS = frozenset({".zip", ".rar", ".7z"})
SIDECAR_EXTS = frozenset({".md", ".txt"})

# ---------------------------------------------------------------------------
# OpenRouter API config
# ---------------------------------------------------------------------------
def _load_env_file() -> None:
    """Load .env / .env.local KEY=VALUE pairs into os.environ (no overwrite)."""
    for name in (".env", ".env.local"):
        p = WORKSPACE_ROOT / name
        if not p.is_file():
            continue
        try:
            for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key, val = key.strip(), val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
        except Exception:
            continue


_load_env_file()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_VISION_MODEL = os.environ.get("OPENROUTER_VISION_MODEL", "qwen/qwen2.5-vl-72b-instruct")
OPENROUTER_TEXT_MODEL = os.environ.get("OPENROUTER_MODEL", "qwen/qwen2.5-vl-72b-instruct")
OPENROUTER_REFERER = os.environ.get("OPENROUTER_HTTP_REFERER", "")
OPENROUTER_TITLE = os.environ.get("OPENROUTER_X_TITLE", "ingest-vectordb")

# ---------------------------------------------------------------------------
# Usage-location rooms (same as ingest_asset.py)
# ---------------------------------------------------------------------------
USAGE_LOCATIONS = (
    "Bar", "Bathroom", "Bedroom", "Balcony", "Café", "Commercial",
    "Dining Room", "Entryway", "Garden", "Garage", "Gym", "Hallway",
    "Hotel", "Kids Room", "Kitchen", "Laundry", "Library", "Living Room",
    "Lobby", "Office", "Outdoor", "Patio", "Restaurant", "Spa", "Street",
    "Study", "Terrace",
)

# ---------------------------------------------------------------------------
# Spinner (simple progress indicator for long model calls)
# ---------------------------------------------------------------------------
class _Spinner:
    def __init__(self, msg: str = "Working") -> None:
        self._msg = msg
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        pct = 0.0
        try:
            while not self._stop.is_set():
                sys.stderr.write(f"\r  {self._msg} {pct:5.1f}%")
                sys.stderr.flush()
                time.sleep(0.15)
                pct = min(pct + 2.5, 95.0)
            sys.stderr.write(f"\r  {self._msg} 100.0%          \n")
            sys.stderr.flush()
        except Exception:
            pass

    def start(self) -> None:
        self._t.start()

    def stop(self) -> None:
        self._stop.set()
        self._t.join()


# ---------------------------------------------------------------------------
# OpenRouter helpers
# ---------------------------------------------------------------------------
def _openrouter_call(
    prompt: str,
    image_path: Path | None = None,
    model: str | None = None,
    timeout: int = 120,
    label: str = "AI call",
) -> str:
    """Call OpenRouter (vision or text) and return the response text."""
    api_key = OPENROUTER_API_KEY or os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing.")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    if OPENROUTER_REFERER:
        headers["HTTP-Referer"] = OPENROUTER_REFERER
    if OPENROUTER_TITLE:
        headers["X-Title"] = OPENROUTER_TITLE

    if image_path is not None:
        use_model = model or OPENROUTER_VISION_MODEL
        ext = image_path.suffix.lower().lstrip(".")
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                "webp": "image/webp"}.get(ext, "image/jpeg")
        b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        payload = {
            "model": use_model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }],
            "temperature": 0,
        }
    else:
        use_model = model or OPENROUTER_TEXT_MODEL
        payload = {
            "model": use_model,
            "messages": [
                {"role": "system", "content": "You are a 3D asset metadata expert. Return ONLY compact JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        }

    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(OPENROUTER_ENDPOINT, data=data_bytes, headers=headers)

    spinner = _Spinner(label)
    spinner.start()
    try:
        max_retries = 4
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                choices = body.get("choices") or []
                if choices:
                    content = (choices[0].get("message") or {}).get("content") or ""
                    if isinstance(content, list):
                        content = "\n".join(
                            p.get("text", "") for p in content if isinstance(p, dict)
                        )
                    return str(content).strip()
                return ""
            except urllib.error.HTTPError as exc:
                if exc.code == 402:
                    print(f"\nERROR: OpenRouter credits exhausted (HTTP 402).", flush=True)
                    raise SystemExit(1)
                if exc.code == 429 and attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"\n  Rate limited. Retrying in {wait}s…", flush=True)
                    time.sleep(wait)
                    continue
                raise
        return ""
    finally:
        spinner.stop()


def _extract_json(text: str) -> dict[str, str]:
    """Parse JSON from AI response, tolerating markdown fences."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return {str(k): "" if v is None else str(v) for k, v in data.items()}
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", cleaned)
    if m:
        try:
            data = json.loads(m.group())
            if isinstance(data, dict):
                return {str(k): "" if v is None else str(v) for k, v in data.items()}
        except json.JSONDecodeError:
            pass
    return {}


# ---------------------------------------------------------------------------
# Deterministic field helpers
# ---------------------------------------------------------------------------
def compute_crc32(file_path: Path) -> str:
    checksum = 0
    with file_path.open("rb") as fh:
        while chunk := fh.read(1024 * 1024):
            checksum = zlib.crc32(chunk, checksum)
    return f"{checksum & 0xFFFFFFFF:08X}"


def author_from_path(path: Path) -> str:
    """Infer author/vendor from first folder under THUMBNAIL_BASE or ARCHIVE_BASE."""
    for base in (THUMBNAIL_BASE, ARCHIVE_BASE):
        try:
            rel = path.resolve().relative_to(base.resolve())
            parts = list(rel.parts)
            if len(parts) >= 2 and parts[0].strip():
                return parts[0].strip()
        except Exception:
            continue
    parent = path.parent.name.strip()
    return parent if parent else "-"


def album_from_path(path: Path) -> str:
    """Infer album/collection from the immediate parent folder name."""
    parent = path.parent.name.strip()
    return parent if parent else "-"


def find_archive_for_image(image_path: Path) -> Path | None:
    """Find the matching archive file in the same directory (shared stem prefix)."""
    parent = image_path.parent
    stem_lower = image_path.stem.lower()
    for ext in ARCHIVE_EXTS:
        for candidate in parent.glob(f"*{ext}"):
            if stem_lower.startswith(candidate.stem.lower()[:8]):
                return candidate
        for candidate in parent.glob(f"*{ext.upper()}"):
            if stem_lower.startswith(candidate.stem.lower()[:8]):
                return candidate
    return None


def find_sidecar_text(image_path: Path) -> str:
    """Look for .md or .txt sidecar file next to the image and return its text."""
    for ext in SIDECAR_EXTS:
        sidecar = image_path.with_suffix(ext)
        if sidecar.exists():
            try:
                return sidecar.read_text(encoding="utf-8", errors="replace").strip()
            except Exception:
                continue
    # Also check for a folder-level sidecar (e.g. catalog text for entire folder)
    for ext in SIDECAR_EXTS:
        for candidate in image_path.parent.glob(f"*{ext}"):
            try:
                text = candidate.read_text(encoding="utf-8", errors="replace").strip()
                if text and len(text) > 20:
                    return text
            except Exception:
                continue
    return ""


# ---------------------------------------------------------------------------
# Vision enrichment — calls the AI model to describe the image
# ---------------------------------------------------------------------------
def vision_describe(image_path: Path, sidecar_text: str = "") -> dict[str, str]:
    """Call the vision model to extract structured metadata from the image.

    Returns a dict with keys: subject, model_name, brand, collection,
    primary_material_or_color, usage_location, shape_form, period, size,
    vendor_name, description.
    """
    location_list = ", ".join(USAGE_LOCATIONS)

    if sidecar_text:
        clean = re.sub(r"^\d+[.)\s]\s*", "", sidecar_text.strip()).strip()
        prompt = (
            "You are a 3D asset metadata expert. "
            "You have two sources: "
            f'(1) Catalogue text: "{clean[:500]}" — use for model_name, brand, collection. '
            "(2) The attached image — use for all visual fields. "
            "Return ONLY a compact JSON object with these exact keys: "
            '"subject", "model_name", "brand", "collection", '
            '"primary_material_or_color", "usage_location", "shape_form", '
            '"period", "size", "vendor_name", "description". '
            "Rules: "
            "(1) subject = CamelCase hierarchy like 'Furniture/Seating/Armchair'. "
            f"(2) usage_location MUST be one of: {location_list}. "
            "(3) size = relative scale descriptor like 'Small', 'Medium', 'Large', 'Oversized'. "
            "(4) description = one-sentence natural language description of the asset. "
            "(5) Use '-' for any field you cannot determine. "
            "(6) Output ONLY JSON. No markdown, no explanation."
        )
    else:
        prompt = (
            "You are a 3D asset metadata expert. "
            "Look at this rendered image and return ONLY a compact JSON object with these exact keys: "
            '"subject", "model_name", "brand", "collection", '
            '"primary_material_or_color", "usage_location", "shape_form", '
            '"period", "size", "vendor_name", "description". '
            "Rules: "
            "(1) subject = CamelCase hierarchy like 'Furniture/Seating/Armchair'. "
            f"(2) usage_location MUST be one of: {location_list}. "
            "(3) size = relative scale descriptor like 'Small', 'Medium', 'Large', 'Oversized'. "
            "(4) description = one-sentence natural language description of the asset. "
            "(5) Use '-' for any field you cannot determine. "
            "(6) Output ONLY JSON. No markdown, no explanation."
        )

    raw = _openrouter_call(prompt, image_path=image_path, label="Vision model")
    return _extract_json(raw)


# ---------------------------------------------------------------------------
# Asset-type detection from filename
# ---------------------------------------------------------------------------
def detect_asset_type(stem: str) -> str:
    """Quick heuristic asset-type detection from filename stem."""
    s = stem.lower()
    if any(k in s for k in ("chair", "sofa", "table", "bed", "shelf", "cabinet", "desk",
                             "bench", "stool", "armchair", "ottoman", "wardrobe", "rug",
                             "curtain", "parasol", "cushion")):
        return "furniture"
    if any(k in s for k in ("lamp", "light", "pendant", "chandelier", "sconce",
                             "spotlight", "walllight", "floorlamp", "fixture",
                             "faucet", "sink", "toilet", "bathtub", "shower")):
        return "fixture"
    if any(k in s for k in ("tree", "plant", "flower", "grass", "shrub", "bush",
                             "cactus", "palm", "ivy", "moss", "fern")):
        return "vegetation"
    if any(k in s for k in ("person", "people", "human", "man", "woman", "child")):
        return "people"
    if any(k in s for k in ("car", "truck", "bike", "vehicle", "bus", "boat")):
        return "vehicle"
    return "furniture"  # default


# ---------------------------------------------------------------------------
# Collect images
# ---------------------------------------------------------------------------
def collect_images(targets: list[Path]) -> list[Path]:
    """Recursively collect image files from the given targets."""
    seen: set[Path] = set()
    result: list[Path] = []
    for target in targets:
        candidates: list[Path] = []
        if target.is_file() and target.suffix.lower() in IMAGE_EXTS:
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
                    result.append(p)
    return sorted(result)


# ---------------------------------------------------------------------------
# Build one vector DB record from a single image
# ---------------------------------------------------------------------------
def build_record(
    image_path: Path,
    force_vision: bool = False,
    existing_records: dict[str, dict] | None = None,
) -> dict[str, str]:
    """Assemble a complete record for one asset image.

    Returns a flat dict with all fields that will be stored in the vector DB.
    """
    resolved = image_path.resolve()

    # -- Deterministic fields --
    rel_path = resolved.as_posix()
    for base in (THUMBNAIL_BASE, ARCHIVE_BASE):
        try:
            rel_path = resolved.relative_to(base.resolve()).as_posix()
            break
        except ValueError:
            continue

    author = author_from_path(resolved)
    album = album_from_path(resolved)
    asset_type = detect_asset_type(resolved.stem)

    # CRC-32 of the image file itself
    crc32 = compute_crc32(resolved)

    # Archive file (if found alongside)
    archive = find_archive_for_image(resolved)
    archive_name = archive.name if archive else "-"

    # -- Sidecar text --
    sidecar = find_sidecar_text(resolved)

    # -- Skip vision if we already have a record and --force-vision is off --
    existing = (existing_records or {}).get(rel_path, {})
    if existing and not force_vision:
        desc = existing.get("description", "")
        if desc and desc != "-":
            # Keep existing AI fields, update deterministic fields
            existing.update({
                "filepath": rel_path,
                "author": author,
                "album": album,
                "asset_type": asset_type,
                "crc32": crc32,
                "archive_file": archive_name,
                "sidecar_text": sidecar or existing.get("sidecar_text", ""),
            })
            return existing

    # -- AI vision enrichment --
    try:
        vision = vision_describe(resolved, sidecar_text=sidecar)
    except Exception as exc:
        print(f"  WARNING: Vision failed for {resolved.name}: {exc}")
        vision = {}

    # Build the combined description text used for embedding
    desc_parts = []
    if vision.get("description") and vision["description"] != "-":
        desc_parts.append(vision["description"])
    if vision.get("subject") and vision["subject"] != "-":
        desc_parts.append(f"Category: {vision['subject']}")
    if vision.get("model_name") and vision["model_name"] != "-":
        desc_parts.append(f"Product: {vision['model_name']}")
    if vision.get("brand") and vision["brand"] != "-":
        desc_parts.append(f"Brand: {vision['brand']}")
    if not desc_parts:
        # Fallback to filename-based description
        stem_text = resolved.stem.replace("_", " ").replace("-", " ")
        parent_text = resolved.parent.name.replace("_", " ")
        desc_parts.append(f"A 3D asset: {stem_text}, from {parent_text}")

    combined_description = ". ".join(desc_parts)

    return {
        "filepath": rel_path,
        # Deterministic
        "author": author,
        "album": album,
        "asset_type": asset_type,
        "crc32": crc32,
        "archive_file": archive_name,
        "filename_stem": resolved.stem,
        # Sidecar
        "sidecar_text": sidecar,
        # AI vision fields
        "subject": vision.get("subject", "-"),
        "model_name": vision.get("model_name", "-"),
        "brand": vision.get("brand", "-"),
        "collection": vision.get("collection", "-"),
        "color": vision.get("primary_material_or_color", "-"),
        "usage_location": vision.get("usage_location", "-"),
        "shape_form": vision.get("shape_form", "-"),
        "period": vision.get("period", "-"),
        "size": vision.get("size", "-"),
        "vendor_name": vision.get("vendor_name", "-"),
        "description": vision.get("description", "-"),
        # Combined text for embedding
        "combined_text": combined_description,
    }


# ---------------------------------------------------------------------------
# LanceDB connection and upsert
# ---------------------------------------------------------------------------
def _connect_lancedb():
    """Connect to LanceDB and return (db, table_or_None)."""
    try:
        import lancedb
    except ImportError:
        sys.exit("[ingest] lancedb not installed. Run: pip install lancedb[embeddings] sentence-transformers")

    db = lancedb.connect(str(LANCEDB_URI))
    tbl = None
    table_list = db.list_tables() if hasattr(db, 'list_tables') else db.table_names()
    if LANCE_TABLE in table_list:
        tbl = db.open_table(LANCE_TABLE)
        print(f"[ingest] Opened existing table '{LANCE_TABLE}'.")
    return db, tbl


def _load_existing_records(tbl) -> dict[str, dict]:
    """Load all existing records keyed by filepath for skip/merge logic."""
    if tbl is None:
        return {}
    try:
        df = tbl.to_pandas()
        records = {}
        for _, row in df.iterrows():
            fp = row.get("filepath", "")
            if fp:
                records[fp] = {k: str(v) if v is not None else "" for k, v in row.items()
                               if k != "vector"}
        return records
    except Exception:
        return {}


def _create_or_get_table(db, tbl, embedding_fn, records: list[dict]):
    """Create table if it doesn't exist, or return existing one."""
    if tbl is not None:
        return tbl

    from lancedb.pydantic import LanceModel, Vector

    class AssetRecord(LanceModel):
        filepath: str
        author: str = ""
        album: str = ""
        asset_type: str = ""
        crc32: str = ""
        archive_file: str = ""
        filename_stem: str = ""
        sidecar_text: str = ""
        subject: str = ""
        model_name: str = ""
        brand: str = ""
        collection: str = ""
        color: str = ""
        usage_location: str = ""
        shape_form: str = ""
        period: str = ""
        size: str = ""
        vendor_name: str = ""
        description: str = ""
        combined_text: str = embedding_fn.SourceField()
        vector: Vector(embedding_fn.ndims()) = embedding_fn.VectorField()

    tbl = db.create_table(LANCE_TABLE, schema=AssetRecord)
    print(f"[ingest] Created new table '{LANCE_TABLE}'.")
    return tbl


def _upsert_batch(tbl, batch: list[dict]) -> None:
    """Upsert a batch of records into the table."""
    (
        tbl.merge_insert("filepath")
           .when_matched_update_all()
           .when_not_matched_insert_all()
           .execute(batch)
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Ingest assets into the LanceDB vector database (source of truth).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "targets", nargs="+",
        help="Folders or image files to index.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be indexed without writing to the DB.",
    )
    parser.add_argument(
        "--force-vision", action="store_true",
        help="Re-run vision model even for assets already in the DB.",
    )
    parser.add_argument(
        "--embed-model", default=EMBEDDING_MODEL,
        help=f"Embedding model (default: {EMBEDDING_MODEL}).",
    )
    parser.add_argument(
        "--embed-device", default=EMBEDDING_DEVICE, choices=["cuda", "cpu"],
        help="Device for embeddings.",
    )
    parser.add_argument(
        "--batch-size", type=int, default=BATCH_SIZE,
        help=f"Upsert batch size (default: {BATCH_SIZE}).",
    )
    args = parser.parse_args()

    # Resolve targets
    targets = []
    for t in args.targets:
        p = Path(t.strip().strip('"'))
        if p.exists():
            targets.append(p)
        else:
            print(f"[ingest] WARNING: target not found: {p}")

    if not targets:
        print("[ingest] No valid targets. Exiting.")
        sys.exit(1)

    # Collect images
    images = collect_images(targets)
    if not images:
        print("[ingest] No images found in targets.")
        sys.exit(0)

    print(f"[ingest] Found {len(images)} images to process.")

    if args.dry_run:
        print("\n--- DRY RUN (no DB writes) ---\n")
        for i, img in enumerate(images[:20], 1):
            author = author_from_path(img)
            album = album_from_path(img)
            sidecar = find_sidecar_text(img)
            archive = find_archive_for_image(img)
            print(f"  {i:3d}. {img.name}")
            print(f"       Author={author}  Album={album}  Archive={archive.name if archive else '-'}")
            if sidecar:
                print(f"       Sidecar: {sidecar[:80]}...")
        if len(images) > 20:
            print(f"  ... and {len(images) - 20} more")
        print(f"\n[ingest] Dry-run complete. {len(images)} images would be indexed.")
        return

    # Load embedding model
    embed_device = args.embed_device
    if embed_device == "cuda":
        try:
            import torch
            if not torch.cuda.is_available():
                print("[ingest] CUDA not available, falling back to CPU.")
                embed_device = "cpu"
        except ImportError:
            embed_device = "cpu"

    print(f"[ingest] Loading embedding model ({args.embed_model}) on {embed_device}...")
    from lancedb.embeddings import get_registry
    embedding_fn = (
        get_registry()
        .get("sentence-transformers")
        .create(name=args.embed_model, device=embed_device)
    )

    # Connect to LanceDB
    db, tbl = _connect_lancedb()
    existing = _load_existing_records(tbl)
    print(f"[ingest] {len(existing)} existing records in DB.")

    # Process images
    records: list[dict] = []
    errors = 0
    skipped = 0

    for i, img in enumerate(images, 1):
        print(f"\n[{i}/{len(images)}] {img.name}")
        try:
            record = build_record(img, force_vision=args.force_vision, existing_records=existing)
            records.append(record)
        except SystemExit:
            raise
        except Exception as exc:
            print(f"  ERROR: {exc}")
            errors += 1
            continue

        # Batch upsert
        if len(records) >= args.batch_size:
            if tbl is None:
                tbl = _create_or_get_table(db, tbl, embedding_fn, records)
            try:
                _upsert_batch(tbl, records)
                print(f"  Upserted batch ({len(records)} records)")
            except Exception as exc:
                print(f"  Batch upsert failed: {exc}")
                errors += len(records)
            records.clear()

    # Flush remaining
    if records:
        if tbl is None:
            tbl = _create_or_get_table(db, tbl, embedding_fn, records)
        try:
            _upsert_batch(tbl, records)
            print(f"  Upserted final batch ({len(records)} records)")
        except Exception as exc:
            print(f"  Final batch upsert failed: {exc}")
            errors += len(records)

    total = len(images)
    success = total - errors - skipped
    print(f"\n[ingest] Done.")
    print(f"  Processed: {success}")
    print(f"  Errors   : {errors}")
    print(f"  Skipped  : {skipped}")
    print(f"  Table    : {LANCE_TABLE}")
    print(f"  LanceDB  : {LANCEDB_URI}")


if __name__ == "__main__":
    main()
