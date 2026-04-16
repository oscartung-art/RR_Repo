from __future__ import annotations

import re
import shutil
import sys
import zlib
import concurrent.futures
import csv
import os
import difflib
from functools import lru_cache
from pathlib import Path

from PIL import Image
import base64
import json
import urllib.error
import urllib.request
import urllib.parse
import html
import threading
import time
import textwrap

# Optional CLIP model support — only needed when USER_LABELS is populated.
# These are lazily imported in load_clip_model() to avoid hard dependency.
# import torch       # optional, used only in score_labels()
# import open_clip   # optional, used only in load_clip_model()

# ---------------------------------------------------------------------------
# ingest_asset.py branch map (detailed)
# ---------------------------------------------------------------------------
#
#   [main()]
#      |
#      +--> parse CLI flags
#      |      (--backend, --enrich-mode, --asset-type, --dry-run, --yes)
#      |
#      +--> backend resolution
#      |      +--> local  -> Ollama calls
#      |      `--> online -> OpenRouter calls (429 retries on model calls)
#      |
#      +--> enrich_mode resolution
#      |      +--> text
#      |      +--> vision
#      |      `--> both
#      |
#      +--> asset_type resolution
#      |      +--> explicit --asset-type? -> use it
#      |      `--> auto-detect path
#      |             +--> source = CLI args (clean_args)
#      |             |      +--> mode=text:
#      |             |      |      detect_asset_category(stem)
#      |             |      |      + interactive: accept / V / manual override
#      |             |      |
#      |             |      +--> mode=vision:
#      |             |      |      detect_asset_category_vision(first_image)
#      |             |      |      (stem ignored for type routing)
#      |             |      |
#      |             |      `--> mode=both:
#      |             |             detect_asset_category(stem)
#      |             |             + if conf != high and image exists:
#      |             |                  detect_asset_category_vision(first_image)
#      |             |
#      |             `--> source = interactive paste paths
#      |                    (same mode policy as above, using first pasted image)
#      |
#      +--> input grouping
#      |      +--> args mode: group by exact stem from CLI file list
#      |      `--> paste mode: read lines, validate files, group by stem
#      |
#      +--> for each stem group
#             +--> not exactly 2 files? -> skip with reason
#             +--> cannot infer image/asset roles? -> skip with reason
#             `--> process_pair(image, asset)
#                    |
#                    +--> validate_inputs(image, asset)
#                    +--> label source
#                    |      +--> vision_detect: classify_image(image)
#                    |      `--> else: CamelCase stem label
#                    +--> compute_crc32(asset)
#                    +--> build_metadata_row(...)
#                    +--> enrich_row_with_models(...)
#                    |      |
#                    |      +--> pass A: web_search_enrich (disabled in vision-only)
#                    |      +--> pass B: enrich_vision_pass (vision/both + image exists)
#                    |      +--> shared field resolver pick()/pick_with_db()
#                    |      +--> deterministic subcategory priorities
#                    |      |      prefix code > db mood code > ai candidate/fuzzy/keywords
#                    |      `--> asset-type branch write
#                    |             + object: dedicated object subcategory matcher + Mood path
#                    |             ` other: generic/category-specific field mapping
#                    |
#                    +--> build_short_base_name(...) + ensure_unique_targets(...)
#                    +--> preview_mapped_metadata(...)
#                    |
#                    +--> dry-run?
#                    |      `--> yes: stop pair here (no move/write)
#                    |
#                    `--> apply stage
#                           +--> require confirm unless --yes
#                           +--> move_pair(image, asset)
#                           `--> append_metadata_row(.metadata.efu)
#

THUMBNAIL_BASE = Path(r"D:\RR_Repo\Database")
ARCHIVE_BASE = Path(r"G:\DB")
# Use a hidden index file to avoid collisions with user files.
METADATA_EFU_PATH = THUMBNAIL_BASE / ".metadata.efu"
# Legacy alias kept for any code that still references OUTPUT_DIR directly.
OUTPUT_DIR = THUMBNAIL_BASE
# Previous DB export used as a supplementary enrichment source.
# Keys are lowercase bare filename stems (no extension, no vendor folder prefix).
CURRENT_DB_PATH = Path(r"E:\Database\CurrentDB.csv")
_CURRENT_DB_CACHE: dict[str, dict[str, str]] | None = None

# Configurable path overrides — set via env vars or CLI flags to remap drives.
_THUMBNAIL_BASE_ENV = os.environ.get("INGEST_THUMBNAIL_BASE", "")
_ARCHIVE_BASE_ENV = os.environ.get("INGEST_ARCHIVE_BASE", "")
if _THUMBNAIL_BASE_ENV:
    THUMBNAIL_BASE = Path(_THUMBNAIL_BASE_ENV)
if _ARCHIVE_BASE_ENV:
    ARCHIVE_BASE = Path(_ARCHIVE_BASE_ENV)
    METADATA_EFU_PATH = THUMBNAIL_BASE / ".metadata.efu"  # recompute if base changed


def _validate_base_paths() -> None:
    """Ensure all required base directories exist before any file operations.

    Exits with a clear error message if a drive is missing or unreachable.
    """
    missing = []
    for label, path in [("THUMBNAIL_BASE (D: drive)", THUMBNAIL_BASE),
                        ("ARCHIVE_BASE (G: drive)", ARCHIVE_BASE)]:
        if not path.exists():
            missing.append(f"  {label}: {path}")
    if missing:
        print("\n[ERROR] Required base paths are missing:")
        for m in missing:
            print(m)
        print("\nCheck that your drives are connected and accessible.")
        print("Override with env vars: INGEST_THUMBNAIL_BASE, INGEST_ARCHIVE_BASE")
        sys.exit(1)


def _load_local_env_vars() -> None:
    """Load simple KEY=VALUE pairs from repo .env files into os.environ.

    Existing environment variables are not overridden.
    """
    repo_root = Path(__file__).resolve().parents[1]
    for env_name in (".env", ".env.local"):
        env_path = repo_root / env_name
        if not env_path.exists() or not env_path.is_file():
            continue
        try:
            for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
        except Exception:
            continue


def _load_current_db() -> dict[str, dict[str, str]]:
    """Lazily load CurrentDB.csv into a stem→row dict (case-insensitive)."""
    global _CURRENT_DB_CACHE
    if _CURRENT_DB_CACHE is not None:
        return _CURRENT_DB_CACHE
    _CURRENT_DB_CACHE = {}
    if not CURRENT_DB_PATH.exists():
        return _CURRENT_DB_CACHE
    try:
        with CURRENT_DB_PATH.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh):
                raw_filename = row.get("Filename", "")
                # Strip vendor sub-folder prefix (e.g. 'designconnected\\')
                bare = raw_filename.replace("\\", "/").split("/")[-1]
                stem = re.sub(r"\.[^.]+$", "", bare).strip().lower()
                if stem:
                    _CURRENT_DB_CACHE[stem] = {
                        k: (v.strip() if v else "") for k, v in row.items()
                    }
    except Exception:
        pass
    return _CURRENT_DB_CACHE


def lookup_current_db(source_stem: str) -> dict[str, str]:
    """Return the matching CurrentDB row for *source_stem*, or empty dict."""
    db = _load_current_db()
    return db.get(source_stem.lower().strip(), {})


# ---------------------------------------------------------------------------
# Keyword file loader — all taxonomy tables live in manual/ingest_keywords.md
# ---------------------------------------------------------------------------

KEYWORDS_MD = Path(__file__).resolve().parents[1] / "manual" / "ingest_keywords.md"


@lru_cache(maxsize=1)
def _load_ingest_keywords() -> dict[str, list[list[str]]]:
    """Parse manual/ingest_keywords.md → section_name: list of data rows.

    Each section starts with a ``## Heading``.  The first pipe-table row in a
    section is the header, the second is the separator (``|---|``); remaining
    rows are data.  Each data row is a list of stripped cell strings.
    """
    if not KEYWORDS_MD.exists():
        return {}
    sections: dict[str, list[list[str]]] = {}
    current: str | None = None
    table_row_idx = 0
    for raw in KEYWORDS_MD.read_text(encoding="utf-8").splitlines():
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


@lru_cache(maxsize=1)
def _kw_prefix_codes() -> dict[str, str]:
    """Return {prefix_code: subcategory} from the Prefix Codes section."""
    rows = _load_ingest_keywords().get("Prefix Codes", [])
    return {r[0]: r[1] for r in rows if len(r) >= 2 and r[0] and r[1]}


@lru_cache(maxsize=1)
def _kw_subcategories() -> set[str]:
    """Return the full set of allowed subcategory names.

    Prefer a human-editable slash-path allowlist under the `## Subcategories`
    heading when present (e.g. `Furniture/Seating/LoungeChair`). If no
    slash-path lines are found, fall back to the existing pipe-table first
    column to remain backwards-compatible.
    """
    # Try to parse slash-path lines from the raw markdown section first.
    slash_paths: list[str] = []
    if KEYWORDS_MD.exists():
        in_section = False
        for raw in KEYWORDS_MD.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("## "):
                in_section = (line[3:].strip() == "Subcategories")
                continue
            if not in_section:
                continue
            if not line:
                continue
            # Skip table rows and markdown separators/code fences
            if line.startswith("|") or line.startswith("---") or line.startswith("```"):
                continue
            # Treat a non-pipe line containing a slash as a path entry
            if "/" in line and re.match(r'^[A-Za-z0-9 _\-\./]+$', line):
                slash_paths.append(line.strip().strip("/"))
    if slash_paths:
        return {p.split("/")[-1] for p in slash_paths if p}

    rows = _load_ingest_keywords().get("Subcategories", [])
    return {r[0] for r in rows if r and r[0]}


@lru_cache(maxsize=1)
def _kw_subcategory_groups() -> dict[str, str]:
    """Return {subcategory: group_path} from the Subcategories section.

    Prefer building the mapping from any slash-path allowlist lines (parent
    path = everything before the final segment). Fall back to the pipe-table
    mapping when no slash-paths are present.
    """
    # Parse slash-path lines first (if present) to build leaf->group mapping.
    slash_paths: list[str] = []
    if KEYWORDS_MD.exists():
        in_section = False
        for raw in KEYWORDS_MD.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("## "):
                in_section = (line[3:].strip() == "Subcategories")
                continue
            if not in_section:
                continue
            if not line:
                continue
            if line.startswith("|") or line.startswith("---") or line.startswith("```"):
                continue
            if "/" in line and re.match(r'^[A-Za-z0-9 _\-\./]+$', line):
                slash_paths.append(line.strip().strip("/"))
    if slash_paths:
        mapping: dict[str, str] = {}
        for path in slash_paths:
            parts = [seg.strip().strip("/") for seg in path.split("/") if seg.strip()]
            if len(parts) >= 2:
                leaf = parts[-1]
                group = "/".join(parts[:-1])
                mapping[leaf] = group
        return mapping

    rows = _load_ingest_keywords().get("Subcategories", [])
    return {r[0]: r[1] for r in rows if len(r) >= 2 and r[0] and r[1]}


@lru_cache(maxsize=1)
def _kw_usage_locations() -> set[str]:
    """Return the set of allowed usage-location room names."""
    rows = _load_ingest_keywords().get("Usage Locations", [])
    return {r[0] for r in rows if r and r[0]}


@lru_cache(maxsize=1)
def _kw_ignore_dirs() -> set[str]:
    """Return the set of folder names to skip during vendor inference."""
    rows = _load_ingest_keywords().get("Ignore Folders", [])
    return {r[0].lower() for r in rows if r and r[0]}


# ---------------------------------------------------------------------------

MODEL_NAME = "ViT-L-14"
PRETRAINED = "openai"
CUSTOM_LABEL_MIN_CONFIDENCE = 0.30
OLLAMA_VISION_MODEL = "qwen3-vl:latest"   # used by enrich_visual.py for material/color/shape
OLLAMA_TEXT_MODEL  = "gemma4:26b"           # fast text pass in ingest_asset.py
OLLAMA_MODEL = OLLAMA_VISION_MODEL           # legacy alias used by classify_image / clean_name_with_qwen
OLLAMA_ENDPOINT = "http://127.0.0.1:11434/api/generate"
# Optional online backend via OpenRouter.
_load_local_env_vars()
# Default model for this script — Gemini 2.5 Flash Lite is the best balance of
# speed, accuracy and cost for furniture brand/metadata extraction via OpenRouter.
# Override with OPENROUTER_MODEL env var or --model=<id> flag.
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash-lite")
OPENROUTER_VISION_MODEL = os.environ.get("OPENROUTER_VISION_MODEL", "qwen/qwen2.5-vl-72b-instruct")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_REFERER = os.environ.get("OPENROUTER_HTTP_REFERER", "")
OPENROUTER_TITLE = os.environ.get("OPENROUTER_X_TITLE", "ingest-asset")
OPENROUTER_FALLBACK_MODELS = [
    m.strip() for m in os.environ.get(
        "OPENROUTER_FALLBACK_MODELS",
        "openai/gpt-4o-mini,google/gemini-2.5-flash,deepseek/deepseek-v3.2",
    ).split(",") if m.strip()
]
ACTIVE_BACKEND = os.environ.get("INGEST_BACKEND", "online").strip().lower() or "online"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
ARCHIVE_EXTENSIONS = {".zip", ".rar", ".7z"}
MODEL_EXTENSIONS = {
    ".abc",
    ".blend",
    ".c4d",
    ".dae",
    ".fbx",
    ".glb",
    ".gltf",
    ".ifc",
    ".ma",
    ".max",
    ".mb",
    ".obj",
    ".ply",
    ".skp",
    ".stl",
    ".usd",
    ".usda",
    ".usdc",
    ".usdz",
    ".3ds",
}
ASSET_FILE_EXTENSIONS = ARCHIVE_EXTENSIONS | MODEL_EXTENSIONS

OLLAMA_BASE_URL = "http://127.0.0.1:11434"


def _check_ollama_available() -> None:
    """Raise RuntimeError immediately if the local Ollama daemon is not reachable.

    Uses a 2-second timeout so callers fail fast instead of hanging for the full
    vision timeout (120 s) when Ollama is not running.
    """
    try:
        with urllib.request.urlopen(OLLAMA_BASE_URL, timeout=2) as resp:
            resp.read()
    except Exception as exc:
        raise RuntimeError(
            f"Vision requires local Ollama running at {OLLAMA_BASE_URL}. "
            "Start Ollama first (e.g. 'ollama serve'), then retry. "
            f"(connection error: {exc})"
        ) from exc


def _openrouter_model_candidates(preferred: str | None = None) -> list[str]:
    """Return an ordered unique list of OpenRouter models to try."""
    candidates: list[str] = []
    first = (preferred or "").strip()
    # Ignore local Ollama model IDs (e.g. gemma4:26b) when using OpenRouter.
    if first and "/" not in first and first != "openrouter/auto":
        first = ""
    if not first:
        first = (OPENROUTER_MODEL or "").strip()
    if first:
        candidates.append(first)
    for m in OPENROUTER_FALLBACK_MODELS:
        if m and m not in candidates:
            candidates.append(m)
    return candidates

# Lookup table: filename prefix code (e.g. "10-01") → canonical CamelCase subcategory.
# Loaded from manual/ingest_keywords.md (## Prefix Codes section).
# This is the highest-priority source for subcategory — overrides vision/text model output.
PREFIX_TO_SUBCATEGORY: dict[str, str] = _kw_prefix_codes()


def _resolve_db_prefix_code(db_mood: str) -> str:
    """Translate a CurrentDB Mood code to a canonical subcategory name.

    CurrentDB stored codes as compact integers (e.g. '1001' instead of '10-01').
    This function normalises both forms and looks them up in PREFIX_TO_SUBCATEGORY.
    Returns the subcategory string, or '' if no match.
    """
    if not db_mood:
        return ""
    v = db_mood.strip()
    # Already formatted like '10-01' — direct lookup.
    if re.match(r"^\d{2}-\d{2}[A-Z]?$", v, re.IGNORECASE):
        return PREFIX_TO_SUBCATEGORY.get(v, "")
    # Compact 4-digit form: '1001' → '10-01'
    if re.match(r"^\d{4}$", v):
        normalised = f"{v[:2]}-{v[2:]}"
        return PREFIX_TO_SUBCATEGORY.get(normalised, "")
    # Compact 3-digit form: '100' → '10-00' (section header, skip)
    return ""


EFU_HEADERS = [
    "Filename",
    "Subject",
    "Rating",
    "Tags",
    "URL",
    "From",
    "Company",
    "Author",
    "Album",
    "custom_property_0",
    "custom_property_1",
    "custom_property_2",
    "Period",
    "Scale",
    "Title",
    "Comment",
    "ArchiveFile",
    "SourceMetadata",
    "Pose",
    "Style",
    "Content Status",
    "custom_property_3",
    "custom_property_4",
    "CRC-32",
]


# Simple spinner for long-running model calls to show activity.
class _Spinner:
    def __init__(self, message: str = "Working") -> None:
        self._msg = message
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._spin, daemon=True)

    # Fixed label width so Vision model / Text model bars stay aligned.
    _LABEL_WIDTH = 16

    def _spin(self) -> None:
        # Show a simple percentage counter instead of a spinner/progress bar.
        progress = 0.0
        step = 3.0
        label = self._msg.ljust(self._LABEL_WIDTH)
        try:
            while not self._stop.is_set():
                try:
                    sys.stderr.write(f"\r{label} {progress:5.1f}%")
                    sys.stderr.flush()
                except Exception as exc:
                    # Log spinner errors instead of silently dying.
                    sys.stderr.write(f"\r{label} [stderr error: {exc}]\n")
                    sys.stderr.flush()
                time.sleep(0.12)
                progress += step
                if progress >= 95.0:
                    # stay near-complete while waiting for the real stop event
                    progress = 90.0
            # on stop, show complete state
            try:
                sys.stderr.write(f"\r{label} 100.0%" + " " * 10 + "\n")
                sys.stderr.flush()
            except Exception as exc:
                sys.stderr.write(f"\r{label} [complete write error: {exc}]\n")
                sys.stderr.flush()
        except Exception as exc:
            # Fallback to a minimal indicator on failure
            try:
                sys.stderr.write(f"\r{label} [spinner error: {exc}]\n")
                sys.stderr.flush()
            except Exception:
                pass

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join()


def _print_help_table() -> None:
    print(textwrap.dedent("""
        ingest_asset  —  Add 3D assets to the local database
        =====================================================
        Reads image + asset-file pairs, fetches metadata (brand, model, category)
        from the web and filename, moves the files into the DB folder, and
        appends a row to .metadata.efu for Everything Search.

        Usage:
          python tools/ingest_asset.py --asset-type=TYPE [OPTIONS] IMAGE ARCHIVE [IMAGE ARCHIVE ...]

          IMAGE    — path to the .jpg / .png render of the asset
          ARCHIVE  — matching archive or 3D model file (same stem as IMAGE)
          TYPE     — one of: furniture | fixture | vegetation | people |
                            material | buildings | layouts

        Options:
          --asset-type=TYPE   (required) Asset category — see TYPE values above
          --backend=MODE      local | online (OpenRouter API)
                    --enrich-mode=MODE  text | vision | both
          --dry-run           Preview result; no files moved, nothing written to index
                    --quick             Legacy alias for --dry-run (accepted for compatibility)
          --yes, -y           Skip confirmation prompt and apply immediately
          -h, --help          Show this help and exit
    """).strip())
    print()
    _print_examples()


def _print_examples() -> None:
    print(textwrap.dedent("""
        Examples:

          # Preview a single furniture asset — nothing is moved or written
          python tools/ingest_asset.py --dry-run --asset-type=furniture
              "G:/3D/designconnected/10-03 mychair.jpg"
              "G:/3D/designconnected/10-03 mychair.rar"

          # Preview a native 3D file pair
          python tools/ingest_asset.py --dry-run --asset-type=furniture
              "G:/3D/designconnected/10-03 mychair.jpg"
              "G:/3D/designconnected/10-03 mychair.glb"

          # Ingest and auto-confirm (no prompt asked)
          python tools/ingest_asset.py --yes --asset-type=furniture
              "G:/3D/designconnected/10-03 mychair.jpg"
              "G:/3D/designconnected/10-03 mychair.rar"

          # Ingest multiple pairs at once
          python tools/ingest_asset.py --yes --asset-type=furniture
              "G:/3D/designconnected/10-03 mychair.jpg"  "G:/3D/designconnected/10-03 mychair.rar"
              "G:/3D/designconnected/10-03 mytable.jpg"  "G:/3D/designconnected/10-03 mytable.rar"

          # Use online backend (OpenRouter API) instead of local Ollama
          python tools/ingest_asset.py --backend=online --dry-run --asset-type=furniture
              "G:/3D/designconnected/10-03 mychair.jpg" "G:/3D/designconnected/10-03 mychair.rar"
    """).strip())
    print()


def _print_progress(current: int, total: int, width: int = 30) -> None:
    if total <= 0:
        return
    pct = (current / total) * 100
    print(f"Progress: {current}/{total} {pct:5.1f}%")


def show_startup_loading(duration: float = 1.2, width: int = 30) -> None:
    """Show a short startup percentage counter for a tidier CLI experience."""
    try:
        print()
        print("Starting ingest tool...")
        for i in range(width + 1):
            pct = i / width
            print(f"\rInitializing {pct*100:5.1f}%", end="", flush=True)
            time.sleep(duration / max(1, width))
        print("\rInitialization complete." + " " * 10)
        print()
    except Exception:
        # Non-fatal; if terminal doesn't support control sequences, skip animation.
        print("Starting ingest tool...")
        time.sleep(0.15)

ASSET_TYPES = {
    "furniture",
    "vegetation",
    "people",
    "texture",
    "material",
    "layouts",
    "fixture",
    "object",
    "vehicle",
    "vfx",
}
PREVIEW_LABELS = {
    "furniture": {
        "Subject": "Subcategory Path",
        "Title": "Model Name",
        "Author": "Vendor Name",
        "Album": "Collection",
        "Genre": "Primary Color/Material",
        "People": "Usage Location",
        "Period": "Period",
        "Scale": "Size",
        "Company": "Brand",
        "From": "From",
        "SourceMetadata": "Category",
    },
    "vegetation": {
        "Subject": "Plant Type",
        "Title": "Approx. Height",
        "Author": "Vendor Name",
        "Album": "Common Name",
        "Genre": "Foliage Color",
        "People": "Growth Location",
        "Company": "Growth Form",
        "Period": "Seasonal Appearance",
        "Scale": "Size",
        "From": "From",
        "SourceMetadata": "Category",
    },
    "people": {
        "Subject": "Original Code Hint",
        "Title": "Gender",
        "Author": "Vendor Name",
        "Album": "Age Group",
        "Genre": "Clothing Color",
        "People": "Scene Context",
        "Period": "Clothing Style",
        "Scale": "Pose / Activity",
        "From": "From",
        "SourceMetadata": "Category",
    },
    "material": {
        "Subject": "Material Name",
        "Genre": "Dominant Color",
        "Company": "Texture Pattern",
        "Period": "Material Category",
        "Scale": "Surface Finish",
        "From": "From",
        "SourceMetadata": "Category",
    },
    "buildings": {
        "Subject": "Subcategory",
        "Company": "Physical Form",
        "Period": "Primary Material",
        "Scale": "Size",
        "From": "From",
        "SourceMetadata": "Category",
    },
    "layouts": {
        "Subject": "Layout Type",
        "Author": "Vendor Name",
        "People": "Room Type",
        "Period": "Layout Shape",
        "From": "From",
        "SourceMetadata": "Category",
    },
    "fixture": {
        "Subject": "Category",
        "Title": "Primary Description",
        "Author": "Vendor Name",
        "Album": "Material",
        "Genre": "Form",
        "People": "Usage Location",
        "Scale": "Size",
        "Company": "Brand",
        "From": "From",
        "SourceMetadata": "Category",
    },
    "object": {
        "Subject": "Subcategory Path",
        "Title": "SubCategory",
        "Author": "Vendor Name",
        "Album": "Collection",
        "Genre": "Primary Color/Material",
        "People": "Usage Location",
        "Period": "Style/Period",
        "Scale": "Size",
        "Company": "Brand",
        "From": "From",
        "SourceMetadata": "Category",
    },
    "vehicle": {
        "Subject": "Type",
        "Title": "Model",
        "Author": "Vendor Name",
        "Genre": "Color",
        "Period": "Year",
        "Scale": "Size",
        "From": "From",
        "SourceMetadata": "Category",
    },
    "vfx": {
        "Subject": "Type",
        "Title": "Description",
        "Genre": "Style/Variant",
        "From": "From",
        "SourceMetadata": "Category",
    },
}
USER_LABELS: list[str] = []


# Physical spaces the model is allowed to use for usage_location.
# Loaded from manual/ingest_keywords.md (## Usage Locations section).
USAGE_LOCATION_ROOMS: set[str] = _kw_usage_locations()


def validate_usage_location(value: str) -> str:
    """Return the value if it matches a known room type; otherwise '-'."""
    if not value or value == "-":
        return "-"
    norm = value.strip().lower()
    for room in USAGE_LOCATION_ROOMS:
        if room.lower() == norm:
            return room
    # Accept if it starts with a known room word (e.g. "outdoor terrace" -> "Outdoor").
    for room in sorted(USAGE_LOCATION_ROOMS, key=len, reverse=True):
        if norm.startswith(room.lower()):
            return room
    return "-"


@lru_cache(maxsize=1)
def load_furniture_subcategories() -> set[str]:
    """Return the full set of allowed subcategory names from manual/ingest_keywords.md."""
    return _kw_subcategories()


def build_mood_hierarchy(subcategory: str) -> str:
    """Return the export hierarchy path for a leaf subcategory.

    Examples:
    - LoungeChair -> Furniture/Seating/LoungeChair
    - SideTable -> Furniture/Table/SideTable
    - Carpet -> Furniture/Carpet
    """
    if not subcategory or subcategory == "-":
        return "-"
    value = subcategory.strip().strip("/")
    if "/" in value:
        return value
    group = _kw_subcategory_groups().get(value, "").strip().strip("/")
    if not group:
        return value
    if group.split("/")[-1].lower() == value.lower():
        return group
    return f"{group}/{value}"


def mood_hierarchy_leaf(value: str) -> str:
    """Return the terminal segment from a Mood hierarchy path."""
    if not value or value == "-":
        return ""
    return value.strip().strip("/").split("/")[-1]


def normalize_furniture_subcategory(candidate: str, source_stem: str, hints: dict[str, str]) -> str:
    allowed = load_furniture_subcategories()
    candidate_clean = sanitize_name_token(candidate)

    # Normalize separators so "low-table" and "low_table" match "low table" keywords.
    stem_lower = re.sub(r"[-_]+", " ", source_stem.lower())

    # Section-header tokens that should not be returned as subcategories.
    # NOTE: only add tokens here that are group/section labels, never leaf subcategories.
    # "Sculpture" was incorrectly listed here — it is a valid leaf subcategory.
    _SECTION_HEADERS = {
        "Table", "Seating", "Lighting", "Storage", "Bed", "Sofa", "Fixtures",
        "Bathroom", "Kitchen", "Outdoor", "Street", "Bar", "Cafe", "Bedroom",
        "Gym", "Office", "Laundry", "Decor", "Furniture", "HVMC",
        "RoomDividers",
    }
    if candidate_clean in _SECTION_HEADERS:
        candidate_clean = ""  # force keyword fallback below

    if candidate_clean and candidate_clean in allowed:
        return candidate_clean

    hint_model = sanitize_name_token(hints.get("model", ""))
    if hint_model in allowed:
        return hint_model

    # Fallback: scan subcategory names directly in the stem (longest match first).
    # CamelCase names are expanded to words: "CoffeeTable" → "coffee table".
    for subcat in sorted(allowed, key=len, reverse=True):
        needle = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", subcat).lower()
        if re.search(r"\b" + re.escape(needle) + r"\b", stem_lower):
            return subcat

    if candidate_clean in {"OutdoorFurniture", "Furniture", "Seating"}:
        return "Sofa" if "Sofa" in allowed else ""

    # Only return candidate if it is actually in the approved list; otherwise unknown.
    return candidate_clean if candidate_clean in allowed else ""


def to_camel_case(label: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", label)
    if not parts:
        raise ValueError("Unable to convert an empty label into CamelCase.")
    return "".join(part[:1].upper() + part[1:] for part in parts)


def build_prompts(labels: list[str]) -> list[str]:
    return [f"a product photo of a {label}" for label in labels]


def prompt_path(prompt_text: str) -> Path:
    raw_value = input(prompt_text).strip().strip('"')
    if not raw_value:
        raise ValueError("A file path is required.")
    path = Path(raw_value)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    return path


def validate_inputs(image_path: Path, archive_path: Path) -> None:
    if not image_path.exists() or not image_path.is_file():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    if not archive_path.exists() or not archive_path.is_file():
        raise FileNotFoundError(f"Asset file not found: {archive_path}")
    if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
        raise ValueError(f"Unsupported image type: {image_path.suffix}")
    if archive_path.suffix.lower() not in ASSET_FILE_EXTENSIONS:
        raise ValueError(f"Unsupported asset file type: {archive_path.suffix}")
    if image_path.stem != archive_path.stem:
        raise ValueError(
            "Image and asset filenames must match exactly before the extension. "
            f"Got '{image_path.stem}' and '{archive_path.stem}'."
        )


def _pair_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in ASSET_FILE_EXTENSIONS:
        return "asset"
    return "other"


def _find_near_counterpart(path: Path, paths: list[Path]) -> Path | None:
    kind = _pair_kind(path)
    wanted = "asset" if kind == "image" else "image" if kind == "asset" else ""
    if not wanted:
        return None

    best_match: Path | None = None
    best_score = 0
    stem_lower = path.stem.lower()
    for other in paths:
        if other == path or other.parent != path.parent:
            continue
        if _pair_kind(other) != wanted:
            continue
        score = len(os.path.commonprefix([stem_lower, other.stem.lower()]))
        if score > best_score:
            best_score = score
            best_match = other
    return best_match if best_score >= 8 else None


def _print_unpaired_group(stem: str, items: list[Path], all_paths: list[Path], indent: str = "") -> None:
    if len(items) != 1:
        print(f"{indent}Skipping '{stem}': expected 2 files, found {len(items)}")
        return

    only = items[0]
    kind = _pair_kind(only)
    counterpart = _find_near_counterpart(only, all_paths)
    if counterpart is not None:
        print(
            f"{indent}Skipping '{stem}': found only {kind} file '{only.name}'. "
            f"Possible counterpart '{counterpart.name}' exists in the same folder, "
            "but the stems do not match exactly. Image and asset filenames must match before the extension."
        )
        return

    if kind in {"image", "asset"}:
        print(
            f"{indent}Skipping '{stem}': found only {kind} file '{only.name}'. "
            "Image and asset filenames must match exactly before the extension."
        )
    else:
        print(f"{indent}Skipping '{stem}': unsupported file '{only.name}'")


def compute_crc32(file_path: Path) -> str:
    checksum = 0
    with file_path.open("rb") as file_handle:
        while chunk := file_handle.read(1024 * 1024):
            checksum = zlib.crc32(chunk, checksum)
    return f"{checksum & 0xFFFFFFFF:08X}"


def normalize_asset_type(raw: str) -> str:
    value = raw.strip().lower()
    if value == "texture":
        return "material"
    return value


def normalize_backend(raw: str) -> str:
    value = (raw or "").strip().lower()
    if value in {"online", "api", "openrouter"}:
        return "online"
    return "local"


def prompt_backend(default_backend: str = "local") -> str:
    default = normalize_backend(default_backend)
    print()
    print("Choose enrichment backend:")
    print("  1) local   (Ollama models)")
    print("  2) online  (OpenRouter API)")
    raw = input(f"Backend [1/2] (default: {default}): ").strip().lower()
    if not raw:
        return default
    if raw in {"1", "l", "local"}:
        return "local"
    if raw in {"2", "o", "online", "api", "openrouter"}:
        return "online"
    return default


def prompt_enrich_mode() -> str:
    """Ask the user which enrichment strategy to use for this session.

    Returns one of: "text" | "vision" | "both"
    """
    print()
    print("Choose enrichment mode:")
    print("  1) text   — filename is descriptive; web/text search fills columns (fast)")
    print("  2) vision — filename is gibberish; vision model fills all columns from the image")
    print("  3) both   — text fills identity fields (brand/model), vision enhances material/color/form")
    raw = input("Mode [1/2/3] (default: 1 - text): ").strip().lower()
    if raw in {"2", "v", "vision"}:
        return "vision"
    if raw in {"3", "b", "both"}:
        return "both"
    return "text"


def prompt_session_context() -> str:
    print()
    print("Session context (optional): describe what you are importing.")
    print("  e.g. 'Importing bathroom faucets from Hansgrohe' or press Enter to skip.")
    raw = input("Context: ").strip()
    return raw


def detect_asset_category(stem: str) -> tuple[str, str]:
    """Use gemma4:26b to auto-detect asset category from filename stem.

    Returns (category, confidence) where confidence is 'high', 'medium', or 'low'.
    Falls back to 'furniture' with 'low' confidence on any error.
    """
    stem_norm = stem.strip().lower()
    if re.match(r"^object(?:$|[_\-\s]|\d)", stem_norm):
        return "object", "high"

    categories = [
        "furniture",   # chairs, tables, sofas, beds, storage, rugs, curtains
        "fixture",     # lighting (lamps, pendants, chandeliers), bathroom, kitchen, appliances
        "vegetation",  # trees, plants, shrubs, flowers, grass
        "object",      # decorative props, books, vases, art, accessories
        "vehicle",     # cars, bikes, trucks, boats
        "people",      # human figures, characters
        "layouts",     # room layouts, floor plans
        "texture",     # textures, surfaces, finishes, fabrics
        "material",    # materials, textures, surfaces, finishes, fabrics
        "vfx",         # visual effects, particles, smoke, fire
    ]
    cat_list = ", ".join(categories)
    prompt = (
        "/no_think "
        "You are a 3D asset classifier. Given a filename stem, return ONLY compact JSON with two keys: "
        '"category" and "confidence". '
        f'"category" MUST be exactly one of: {cat_list}. '
        '"confidence" MUST be exactly one of: "high", "medium", "low". '
        "Rules: "
        "- furniture = chairs, tables, sofas, beds, storage, rugs, curtains, parasols. "
        "- fixture = ALL lighting (lamps, pendants, chandeliers, wall lights, floor lamps, table lamps), "
        "  bathroom fittings, kitchen appliances, gym equipment, HVAC. "
        "- vegetation = trees, plants, shrubs, flowers, grass, cacti, moss. "
        "- object = decorative props, vases, books, art, accessories, small items. "
        "- texture = textures, surfaces, finishes, fabrics, flooring. "
        "- material = materials and textures, combined asset types. "
        "Use 'low' confidence when the filename is ambiguous or too abbreviated to be sure. "
        "No explanation. No extra keys. "
        f"Filename stem: {stem}"
    )
    try:
        raw = ollama_generate(
            prompt=prompt,
            image_path=None,
            timeout=45,
            model=OLLAMA_TEXT_MODEL,
            spinner_label="Category detect...",
        )
        data = extract_json_payload(raw)
        cat = (data.get("category") or "").strip().lower()
        conf = (data.get("confidence") or "low").strip().lower()
        cat = normalize_asset_type(cat)
        if cat in ASSET_TYPES:
            return cat, conf
    except Exception:
        pass
    return "furniture", "low"


def detect_asset_category_vision(image_path: Path) -> tuple[str, str]:
    """Use Ollama vision model to classify a 3D asset category from its render image.

    Returns (category, confidence) in the same format as detect_asset_category.
    Falls back to 'furniture' with 'low' confidence on any error.
    """
    categories = [
        "furniture",   # chairs, tables, sofas, beds, storage, rugs, curtains
        "fixture",     # lighting, bathroom fittings, kitchen appliances, HVAC
        "vegetation",  # trees, plants, shrubs, flowers, grass
        "object",      # decorative props, vases, books, art, accessories
        "material",    # textures, surfaces, finishes, fabrics
        "vehicle",     # cars, bikes, trucks, boats
        "people",      # human figures, characters
        "buildings",   # architecture, structures, facades
        "layouts",     # room layouts, floor plans
        "vfx",         # visual effects, particles, smoke, fire
        "procedural",  # procedural/parametric assets
        "location",    # environments, landscapes, cityscapes
    ]
    cat_list = ", ".join(categories)
    prompt = (
        "/no_think "
        "You are a 3D asset classifier. Look at the image and return ONLY compact JSON with two keys: "
        '"category" and "confidence". '
        f'"category" MUST be exactly one of: {cat_list}. '
        '"confidence" MUST be exactly one of: "high", "medium", "low". '
        "Rules: "
        "- furniture = chairs, tables, sofas, beds, storage, rugs, curtains, parasols. "
        "- fixture = ALL lighting (lamps, pendants, chandeliers, wall lights, floor lamps, table lamps), "
        "  bathroom fittings, kitchen appliances, gym equipment, HVAC. "
        "- vegetation = trees, plants, shrubs, flowers, grass, cacti, moss. "
        "- object = decorative props, vases, books, art, accessories, small items. "
        "- material = textures, surfaces, finishes, fabrics, flooring. "
        "Use 'low' confidence when the image is ambiguous. "
        "No explanation. No extra keys."
    )
    raw = ollama_generate(prompt, image_path=image_path, timeout=120, spinner_label="Vision detect... ")
    try:
        data = extract_json_payload(raw)
        cat = normalize_asset_type((data.get("category") or "").strip().lower())
        conf = (data.get("confidence") or "low").strip().lower()
        if cat in ASSET_TYPES:
            return cat, conf
    except Exception:
        pass
    return "furniture", "low"


def enrich_vision_pass(
    image_path: Path,
    asset_type: str,
    subcats_list: str,
    location_list: str,
) -> dict[str, str]:
    """Use the local Ollama vision model to extract all EFU metadata fields from a render image.

    Returns a dict with the same keys used by web_search_enrich (e.g. subcategory,
    model_name, brand, primary_material_or_color, shape_form, etc).
    """
    prompt = (
        f"You are a 3D asset metadata expert for {asset_type} items. "
        "Look at this rendered image and return ONLY a compact JSON object with these exact keys: "
        '"subcategory", "model_name", "brand", "collection", '
        '"primary_material_or_color", "usage_location", "shape_form", "period", "size", "vendor_name". '
        "STRICT rules: "
        f"(1) subcategory MUST be exactly one value from this list: {subcats_list}. "
        f"(2) usage_location MUST be exactly one value from this list: {location_list}. "
        "(3) Use '-' for any field you cannot confidently determine from the image. "
        "(4) Output ONLY the JSON object. No markdown, no explanation, no extra keys."
    )
    raw = ollama_generate(prompt, image_path=image_path, timeout=120, spinner_label="Vision enrich... ")
    return extract_json_payload(raw)


def prompt_asset_type() -> str:
    # Present a compact numbered menu and accept number, short abbreviation or full name.
    options = [
        ("furniture", "Furniture", "F"),
        ("vegetation", "Vegetation", "V"),
        ("people", "People", "P"),
        ("material", "Material", "M"),
        ("buildings", "Buildings", "B"),
        ("layouts", "Layouts", "L"),
        ("fixture", "Fixture", "T"),
        ("object", "Object", "O"),
        ("procedural", "Procedural", "R"),
        ("location", "Location", "C"),
        ("vehicle", "Vehicle", "H"),
        ("vfx", "VFX", "X"),
    ]
    print()
    print("Select asset type:")
    # Render as a compact ASCII table for better scanning.
    num_w = len(str(len(options)))
    key_w = max(len(k) for k, _, _ in options)
    label_w = max(len(label) for _, label, _ in options)
    abbr_w = max(len(abbr) for _, _, abbr in options)
    header = f"  {'No'.rjust(num_w)} | {'Key'.ljust(key_w)} | {'Label'.ljust(label_w)} | {'Abbr'.ljust(abbr_w)}"
    sep = '  ' + '-' * (len(header) - 2)
    print(header)
    print(sep)
    for idx, (key, label, abbr) in enumerate(options, start=1):
        print(f"  {str(idx).rjust(num_w)} | {key.ljust(key_w)} | {label.ljust(label_w)} | {abbr.center(abbr_w)}")
    print(sep)
    raw = input("Choose (number, letter, or name): ").strip()
    if not raw:
        raise ValueError("Asset type is required.")

    # Numeric selection
    if raw.isdigit():
        n = int(raw)
        if 1 <= n <= len(options):
            return options[n - 1][0]

    norm = raw.strip().lower()
    # Allow single-letter abbreviations mapping
    abbr_map = {abbr.lower(): key for key, _, abbr in options}
    if norm in abbr_map:
        return abbr_map[norm]

    # Allow names and small synonyms
    norm2 = normalize_asset_type(norm)
    if norm2 in ASSET_TYPES:
        return norm2

    # Fallback: try direct match against option labels
    for key, label, _ in options:
        if norm == label.lower() or norm == key:
            return key

    raise ValueError(f"Unsupported asset type: {raw}")


def parse_filename_hints(stem: str) -> dict[str, str]:
    parts = [p.strip() for p in stem.split(".") if p.strip()]
    first = parts[0] if parts else stem
    first_words = first.split()
    lead_code = first_words[0] if first_words else ""
    lead_desc = " ".join(first_words[1:]).strip() if len(first_words) > 1 else first
    model_raw = parts[1] if len(parts) > 1 else ""
    collection_raw = parts[2] if len(parts) > 2 else ""
    brand_raw = parts[3] if len(parts) > 3 else ""

    def humanize(value: str) -> str:
        return re.sub(r"\s+", " ", value.replace("_", " ").replace("-", " ")).strip()

    brand_clean = re.sub(r"\d+$", "", brand_raw).strip() or brand_raw
    all_text = humanize(stem).lower()
    size_match = re.search(r"\b\d+\s*[xX]\s*\d+\b", stem)

    return {
        "uid": lead_code,
        "lead_desc": humanize(lead_desc),
        "model": humanize(model_raw),
        "collection": humanize(collection_raw),
        "brand": humanize(brand_clean),
        "brand_raw": humanize(brand_raw),
        "size": size_match.group(0).replace(" ", "") if size_match else "",
        "all_text": all_text,
    }


def clean_display_case(value: str) -> str:
    """Normalize casing for display fields while preserving existing mixed-case tokens."""
    value = value.strip()
    if not value:
        return ""
    out: list[str] = []
    for token in value.split():
        if any(ch.isupper() for ch in token[1:]):
            out.append(token)
        elif token.isupper() and len(token) <= 4:
            out.append(token)
        else:
            out.append(token[:1].upper() + token[1:].lower())
    return " ".join(out)


def clean_name_with_qwen(asset_type: str, source_stem: str, mapped_subcategory: str, mapped_brand: str) -> str:
    """Use local Ollama model to clean noisy source filename into a concise semantic name."""
    prompt = (
        "Create a short clean asset filename from noisy text. "
        "Rules: remove ids/codes/checksums/numbers unless part of product model, "
        "output 1-3 words in CamelCase separated by underscore, no extension, no explanation. "
        f"Asset type: {asset_type}. Source: {source_stem}. "
        f"Subcategory hint: {mapped_subcategory}. Brand hint: {mapped_brand}."
    )
    text = ollama_generate(
        prompt=prompt,
        timeout=45,
        spinner_label="Name cleanup...",
    ).splitlines()[0].strip()
    # Preserve hyphens and accented characters common in European brand names.
    text = re.sub(r"[^A-Za-z0-9_\-\u00C0-\u024F]+", "_", text)
    return text


def ollama_generate(
    prompt: str,
    image_path: Path | None = None,
    timeout: int = 90,
    model: str | None = None,
    spinner_label: str | None = None,
) -> str:
    backend = normalize_backend(ACTIVE_BACKEND)

    if backend == "local":
        payload = {
            "model": model or OLLAMA_VISION_MODEL,
            "prompt": prompt,
            "stream": False,
        }
        if image_path is not None:
            payload["images"] = [base64.b64encode(image_path.read_bytes()).decode("utf-8")]

        req = urllib.request.Request(
            OLLAMA_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        spinner_msg = spinner_label or ("Vision model..." if image_path is not None else "Text model...")
        spinner = _Spinner(spinner_msg)
        spinner.start()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        finally:
            try:
                spinner.stop()
            except Exception:
                pass
        return (body.get("response") or "").strip()

    api_key = OPENROUTER_API_KEY.strip() or os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing. Set it in the same terminal session or add it to .env"
        )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    if OPENROUTER_REFERER:
        headers["HTTP-Referer"] = OPENROUTER_REFERER
    if OPENROUTER_TITLE:
        headers["X-Title"] = OPENROUTER_TITLE

    # Online vision: image present → use OpenRouter vision model (qwen2.5-vl or override).
    if image_path is not None:
        _vision_model = model if (model and "/" in model) else OPENROUTER_VISION_MODEL
        _suffix = image_path.suffix.lower().lstrip(".")
        _mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(_suffix, "image/jpeg")
        _img_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        _vis_payload = {
            "model": _vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{_mime};base64,{_img_b64}"}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "temperature": 0,
        }
        _vis_req = urllib.request.Request(
            OPENROUTER_ENDPOINT,
            data=json.dumps(_vis_payload).encode("utf-8"),
            headers=headers,
        )
        spinner_msg = spinner_label or f"Vision ({_vision_model.split('/')[-1]})..."
        _vis_body: dict = {}
        _vis_max_retries = 4
        for _vis_attempt in range(_vis_max_retries):
            spinner = _Spinner(spinner_msg)
            spinner.start()
            try:
                with urllib.request.urlopen(_vis_req, timeout=timeout) as resp:
                    _vis_body = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as _ve:
                if _ve.code == 429 and _vis_attempt < _vis_max_retries - 1:
                    _wait = 2 ** _vis_attempt  # 1s, 2s, 4s
                    print(f"\n  Rate limited (429). Retrying vision in {_wait}s…", flush=True)
                    time.sleep(_wait)
                    continue
                raise
            finally:
                try:
                    spinner.stop()
                except Exception:
                    pass
        else:
            raise RuntimeError("Vision call failed after retries (persistent 429)")
        _choices = _vis_body.get("choices") or []
        if _choices:
            return ((_choices[0].get("message") or {}).get("content") or "").strip()
        return ""

    model_candidates = _openrouter_model_candidates(model)
    if not model_candidates:
        raise RuntimeError("No OpenRouter model configured. Set OPENROUTER_MODEL or OPENROUTER_FALLBACK_MODELS")

    spinner_msg = spinner_label or "OpenRouter..."
    body: dict = {}
    last_error = ""
    unavailable_models: list[str] = []
    for idx, model_name in enumerate(model_candidates):
        # Add a system prompt for cloud models — significantly improves JSON
        # compliance and brand/model field separation vs a bare user message.
        _system_prompt = (
            "You are a 3D asset metadata expert specialising in furniture, lighting, "
            "and decor brands. Extract structured metadata from filename stems. "
            "Always return ONLY compact JSON — no markdown, no explanation. "
            "Use '-' for any field you cannot confidently identify."
        )
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": _system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        }
        req = urllib.request.Request(
            OPENROUTER_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
        )

        model_succeeded = False
        max_retries = 4
        for attempt in range(max_retries):
            spinner = _Spinner(spinner_msg)
            spinner.start()
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                model_succeeded = True
                break
            except urllib.error.HTTPError as exc:
                details = ""
                try:
                    details = exc.read().decode("utf-8", errors="replace")[:500]
                except Exception:
                    details = str(exc)
                # 402 = Payment Required — credits exhausted. Abort the entire run immediately
                # so it doesn't silently process hundreds of assets with blank metadata.
                # SystemExit is a BaseException and bypasses all broad `except Exception` blocks.
                if exc.code == 402:
                    print(f"\nERROR: OpenRouter credits exhausted (HTTP 402). Top up your account.\nDetails: {details[:300]}", flush=True)
                    raise SystemExit(1)
                lower = details.lower()
                model_unavailable = (
                    exc.code in {400, 403, 404}
                    and ("not available" in lower or "not found" in lower or "does not exist" in lower)
                )
                if model_unavailable:
                    unavailable_models.append(model_name)
                    if idx < len(model_candidates) - 1:
                        break
                    tried = ", ".join(unavailable_models) if unavailable_models else model_name
                    raise RuntimeError(
                        "OpenRouter models unavailable for this account/region. "
                        f"Tried: {tried}. Set OPENROUTER_MODEL or OPENROUTER_FALLBACK_MODELS."
                    ) from exc

                last_error = f"OpenRouter HTTP {exc.code}: {details}"
                if exc.code == 429 and attempt < max_retries - 1:
                    _wait = 2 ** attempt  # 1s, 2s, 4s
                    print(f"\n  Rate limited (429). Retrying in {_wait}s…", flush=True)
                    time.sleep(_wait)
                    continue
                break
            finally:
                try:
                    spinner.stop()
                except Exception:
                    pass

        if model_succeeded:
            break
    else:
        raise RuntimeError(last_error or "OpenRouter request failed for all candidate models")

    content = ""
    try:
        msg = (body.get("choices") or [{}])[0].get("message", {})
        content = msg.get("content") or ""
        if isinstance(content, list):
            chunks: list[str] = []
            for part in content:
                if isinstance(part, dict):
                    txt = part.get("text")
                    if txt:
                        chunks.append(str(txt))
            content = "\n".join(chunks)
    except Exception:
        content = ""
    return str(content).strip()


def extract_json_payload(text: str) -> dict[str, str]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return {str(k): "" if v is None else str(v) for k, v in data.items()}
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
        if isinstance(data, dict):
            return {str(k): "" if v is None else str(v) for k, v in data.items()}
    except json.JSONDecodeError:
        return {}
    return {}




# ---------------------------------------------------------------------------
# Pass 3 — Web search → page fetch → LLM extract
# ---------------------------------------------------------------------------

# Trusted design/product domains ranked by reliability for furniture/lighting.
_TRUSTED_DOMAINS = (
    # Manufacturer sites (highest trust)
    "foscarini.com", "knoll.com", "cassina.com", "vitra.com",
    "flos.com", "artemide.com", "minotti.com", "poliform.com",
    "moooi.com", "fritzhansen.com", "hermanmiller.com",
    "kartell.com", "zanotta.com", "moroso.com", "dedon.de",
    "desede.com", "bb-italia.it", "flexform.it", "boffi.com",
    "ideal-lux.com", "prandina.it", "luceplan.com",
    # Design databases / catalogues
    "turbosquid.com",
    "archiexpo.com", "archiproducts.com", "architonic.com",
    "stylepark.com", "andlight.com", "ambientedirect.com",
    "designboom.com", "dezeen.com", "wallpaper.com",
    "designartmagazine.com", "studiodimensione", "distrettodesign",
    "dammidesign.it", "pamono.com", "1stdibs.com", "yliving.com",
    "connox.com", "light11.eu", "chaplins.co.uk",
)

# Retail/marketplace domains to deprioritize (ranked last)
_RETAIL_DOMAINS = (
    "amazon.com", "amazon.co", "ebay.com", "walmart.com",
    "wayfair.com", "overstock.com", "homedepot.com", "lowes.com",
    "target.com", "ikea.com",
)


def _ddg_search_urls(query: str, max_results: int = 8) -> list[str]:
    """Return up to *max_results* URLs from a DuckDuckGo HTML search."""
    encoded = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; AssetIngestor/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            body = r.read().decode("utf-8", errors="replace")
    except Exception:
        return []
    # Extract result URLs from DuckDuckGo HTML (href in result__a links)
    # DDG's HTML structure changes frequently — try multiple patterns as fallback.
    urls: list[str] = []
    patterns = [
        r'class="result__a"[^>]*href="([^"]+)"',
        r'class="result__url"[^>]*href="([^"]+)"',
        r'<a[^>]*class="[^"]*result[^"]*"[^>]*href="([^"]+)"',
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, body):
            href = html.unescape(m.group(1))
            qs = urllib.parse.urlparse(href).query
            params = urllib.parse.parse_qs(qs)
            actual = params.get("uddg", [href])[0]
            if actual.startswith("http"):
                urls.append(actual)
            if len(urls) >= max_results:
                break
        if urls:
            break
    if not urls:
        # DDG returned no results — log for diagnostics.
        pass
    return urls


def _fetch_page_text(url: str, max_chars: int = 8000) -> str:
    """Fetch a URL and return stripped plain text (no HTML tags), truncated.

    Increased default from 3000 to 8000 chars to capture product details
    that appear deeper in the page (brand names, model numbers, specs).
    """
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; AssetIngestor/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            raw = r.read().decode("utf-8", errors="replace")
    except Exception:
        return ""
    # Strip script/style blocks
    raw = re.sub(r"<(script|style)[^>]*>[\s\S]*?</\1>", " ", raw, flags=re.IGNORECASE)
    # Extract useful structured content first (headings, meta, product titles)
    structured = ""
    for tag in ("h1", "h2", "h3", "title", "meta"):
        for m in re.finditer(rf"<{tag}[^>]*>(.*?)</{tag}>", raw, re.IGNORECASE | re.DOTALL):
            structured += re.sub(r"<[^>]+>", " ", m.group(1)) + "\n"
    # Strip all remaining tags
    text = re.sub(r"<[^>]+>", " ", raw)
    # Collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = html.unescape(text).strip()
    return text[:max_chars]


# Known vendor slug patterns → vendor name used for targeted site search
_VENDOR_SITE_MAP: dict[str, str] = {
    "designconnected": "designconnected.com",
    "design-connected": "designconnected.com",
}


def _detect_vendor_site(source_path: str) -> str | None:
    """Return a site: search domain if the source path implies a known vendor."""
    lower = source_path.lower().replace("\\", "/")
    for slug, site in _VENDOR_SITE_MAP.items():
        if slug in lower:
            return site
    return None


def web_search_enrich(
    product_query: str,
    schema_keys: list[str],
    subcats_list: str,
    location_list: str,
    session_hint_str: str = "",
    source_path: str = "",
    subcategory_hint: str = "",
) -> dict[str, str]:
    """Search the web for *product_query*, fetch the most relevant pages,
    and use the LLM to extract furniture metadata from the page content.

    If *source_path* hints at a known vendor (e.g. a path containing
    'designconnected'), the search is scoped to that vendor's site first
    for much higher accuracy on vendor-specific slug filenames.

    Returns a (possibly partial) dict with the same keys as schema_keys.
    Returns empty dict on no-result cases. Request/model failures are returned
    as {"_error": "..."} so callers can surface diagnostics instead of
    failing silently.
    """
    vendor_site = _detect_vendor_site(source_path) if source_path else None

    # --- Strategy 1: vendor-scoped search (high precision) ---
    # For DesignConnected specifically, also search TurboSquid mirror pages
    # because designconnected.com loads brand names via JS (invisible to plain fetch),
    # while TurboSquid mirrors include the full brand in static HTML.
    urls: list[str] = []
    if vendor_site:
        scoped_query = f"site:{vendor_site} {product_query}"
        urls = _ddg_search_urls(scoped_query, max_results=6)
        if vendor_site == "designconnected.com":
            # Also search TurboSquid for the same product — brand is in static HTML there
            ts_urls = _ddg_search_urls(
                f"site:turbosquid.com {product_query} designconnected", max_results=4
            )
            # Interleave: DC page first (for model name), TS page second (for brand)
            urls = urls[:3] + ts_urls[:2] + urls[3:]

    # --- Strategy 2: broad design/furniture search (fallback) ---
    if not urls:
        _broad_hint = subcategory_hint or "designer furniture lighting brand"
        urls = _ddg_search_urls(f"{product_query} {_broad_hint}", max_results=12)
    if not urls:
        return {"_error": "no search results from DuckDuckGo"}

    # Prefer trusted design/product domains; fall back to whatever DDG returned.
    def _domain_rank(u: str) -> int:
        # Retail sites always go last
        for d in _RETAIL_DOMAINS:
            if d in u:
                return len(_TRUSTED_DOMAINS) + 100
        for i, d in enumerate(_TRUSTED_DOMAINS):
            if d in u:
                return i
        return len(_TRUSTED_DOMAINS)

    urls.sort(key=_domain_rank)

    page_text = ""
    used_url = ""
    for u in urls[:6]:
        # Skip bare homepages — they have no product-specific content.
        # A URL is a homepage if its path is empty, '/', or just a locale code.
        parsed_path = urllib.parse.urlparse(u).path.strip("/")
        if not parsed_path or re.fullmatch(r'[a-z]{2}(-[a-z]{2})?', parsed_path):
            continue
        t = _fetch_page_text(u)
        if len(t) > 200:
            page_text = t
            used_url = u
            break

    if not page_text:
        return {"_error": "no usable page content found"}

    schema_text = ", ".join(schema_keys)
    prompt = (
        "You are a strict furniture metadata extractor. "
        f"{session_hint_str}"
        f"The product being searched is: '{product_query}'. "
        "Below is text scraped from a product/design website. "
        "Extract the furniture metadata and return ONLY compact JSON with these exact keys: "
        f"{schema_text}. "
        "STRICT rules: "
        "(1) Use '-' for any field you cannot confidently extract from the text. "
        f"(2) subcategory MUST be one of: {subcats_list}. "
        "(3) brand must be ONLY the manufacturer name, NOT the designer name. "
        "(4) model_name is the product name, NOT a category. "
        f"(5) usage_location MUST be one of: {location_list}. "
        "(6) No extra keys, no explanation. "
        f"Page text:\n{page_text}"
    )
    try:
        raw = ollama_generate(
            prompt=prompt,
            timeout=60,
            model=OLLAMA_TEXT_MODEL,
            spinner_label="Web extract...",
        )
        result = extract_json_payload(raw)
        if used_url and result:
            result["_web_url"] = used_url  # carry URL for DB storage
        return result
    except Exception as exc:
        return {"_error": str(exc)}


def enrich_row_with_models(
    image_path: Path,
    source_stem: str,
    asset_type: str,
    hints: dict[str, str],
    row: dict[str, str],
    session_context: str = "",
    session_hints: dict[str, str] | None = None,
    enrich_mode: str = "both",
) -> dict[str, str]:
    """Metadata enrichment pipeline to fill metadata columns from web search.

    Web pass:  DuckDuckGo search → fetch product page → LLM extract.
               Runs for all assets. Returns canonical brand names, correct
               brand/designer separation, and subcategory from real product data.
               Visual fields (Genre/Company/Period) also filled if found on page.
    """
    # All asset types flow through this enrichment pipeline in both text and vision modes.
    # Prefix codes resolve subcategory for every category; the web pass
    # additionally fills brand/model/collection fields when a useful query can be built.

    vision_data: dict[str, str] = {}   # kept for pick() compatibility; always empty here
    text_data: dict[str, str] = {}     # kept for pick() compatibility; always empty here
    # Diagnostics placeholders retained for backward compatibility with the
    # existing Comment-field trace logic at the end of this function.
    vision_error = ""
    text_error = ""

    # Build subcategory list scoped to the actual asset_type so the vision prompt
    # receives the correct candidates (e.g. Object subcats for object type, not Furniture).
    _type_prefix = asset_type.capitalize()  # "furniture" -> "Furniture", "object" -> "Object", etc.
    _all_groups = _kw_subcategory_groups()
    _type_subcats = sorted(
        subcat for subcat, grp in _all_groups.items()
        if grp.lower().startswith(_type_prefix.lower())
    )
    allowed_subcats = _type_subcats if _type_subcats else sorted(load_furniture_subcategories())
    subcats_list = ", ".join(allowed_subcats)
    location_list = ", ".join(sorted(USAGE_LOCATION_ROOMS))

    session_hint_str = ""
    if session_context:
        session_hint_str = f"Session context from user: '{session_context}'. "
    sh = session_hints or {}

    # Pass 1 — Web search: skipped in vision-only mode.
    web_data: dict[str, str] = {}
    _clean_stem = re.sub(r'^[\d\s\-\.]+', '', source_stem).strip()
    _web_query = (_clean_stem or source_stem).replace(".", " ").replace("_", " ").replace("-", " ")

    # Pre-compute the subcategory hint from the UID prefix so it can be injected
    # into the DDG query — e.g. '10-13' -> 'CoffeeTable' -> 'coffee table'.
    _early_uid = (hints.get("uid", "") or "").strip()
    _early_subcat = PREFIX_TO_SUBCATEGORY.get(_early_uid, "") if _early_uid else ""
    _subcat_hint_words = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', _early_subcat).lower().strip()
    if _subcat_hint_words and _subcat_hint_words not in _web_query.lower():
        _web_query = f"{_web_query} {_subcat_hint_words}".strip()

    # Web pass uses the full schema so it can also fill visual fields if available
    _full_schema_keys = [
        "subcategory", "model_name", "brand", "collection",
        "primary_material_or_color", "usage_location", "shape_form",
        "period", "size", "vendor_name",
    ]
    if enrich_mode != "vision":
        web_data = web_search_enrich(
            product_query=_web_query,
            schema_keys=_full_schema_keys,
            subcats_list=subcats_list,
            location_list=location_list,
            session_hint_str=session_hint_str,
            source_path=str(image_path),
            subcategory_hint=_subcat_hint_words if _subcat_hint_words else "",
        )
        text_error = (web_data.pop("_error", "") or "").strip()
        if text_error and "429" in text_error:
            print(
                f"  Web extract rate-limited for {image_path.name}; continuing with deterministic fallbacks.",
                flush=True,
            )
        # Store the source URL in the row if found
        _web_url = web_data.pop("_web_url", "")
        if _web_url and not row.get("URL", "").strip():
            row["URL"] = _web_url

    # Vision pass: populates vision_data when enrich_mode is "vision" or "both".
    if enrich_mode in ("vision", "both") and image_path.exists():
        try:
            vision_data = enrich_vision_pass(image_path, asset_type, subcats_list, location_list)
        except Exception as _ve:
            vision_error = str(_ve)
            if "429" in vision_error:
                print(
                    f"  Vision rate-limited for {image_path.name}; continuing without vision fields.",
                    flush=True,
                )

    # Text pass removed — web pass is the sole text enrichment path.
    # Tests showed web pass is strictly superior: better brand name formatting,
    # correct brand vs designer separation, and handles all stem types equally well.

    def pick(key: str, fallback: str = "-") -> str:
        wval = (web_data.get(key, "") or "").strip()
        tval = (text_data.get(key, "") or "").strip()
        vval = (vision_data.get(key, "") or "").strip()
        if wval and wval != "-":
            return wval
        if tval and tval != "-":
            return tval
        if vval and vval != "-":
            return vval
        return fallback

    # Useful deterministic fallback for stems like "nestrest-by-dedon".
    by_brand_match = re.search(r"\bby[-_\s]+([A-Za-z0-9]+)\b", source_stem, flags=re.IGNORECASE)
    by_brand = clean_display_case(by_brand_match.group(1)) if by_brand_match else ""

    # ── Subcategory resolution (highest → lowest priority) ───────────────
    # Consult the legacy DB for this stem — used as high-priority prefix source
    # and low-priority fallback for other fields.
    db_row = lookup_current_db(source_stem)

    def db_get(efu_key: str) -> str:
        """Return the DB value for the given EFU column if non-trivial."""
        v = db_row.get(efu_key, "").strip()
        return v if v and v not in ("-", "0") else ""

    def pick_with_db(ai_key: str, efu_key: str, fallback: str = "-") -> str:
        """AI output → DB fallback → row default → hardcoded fallback."""
        ai = pick(ai_key, "")
        if ai and ai != "-":
            return ai
        db_val = db_get(efu_key)
        if db_val:
            return db_val
        row_val = row.get(efu_key, "").strip()
        if row_val and row_val != "-":
            return row_val
        return fallback

    # 1. Filename prefix code (e.g. '10-01' in the stem) — fully deterministic.
    _uid = hints.get("uid", "")
    _uid_subcategory = PREFIX_TO_SUBCATEGORY.get(_uid, "") if _uid else ""

    # 2. DB Mood column — may be stored as '1001' (needs normalisation to '10-01').
    _db_subcategory = _resolve_db_prefix_code(db_get("Mood"))

    # 3. AI model output — used only when both deterministic sources miss.
    # Use the type-scoped allowed_subcats (already built above) so that object/sculpture,
    # vegetation/tree, etc. are matched correctly — not just furniture subcategories.
    _ai_candidate = pick("subcategory", row.get("Subject", "-"))
    _ai_candidate_clean = sanitize_name_token(_ai_candidate)
    if _ai_candidate_clean in allowed_subcats:
        _ai_subcategory = _ai_candidate_clean
    else:
        _ai_subcategory = ""
        # Fuzzy / substring match of the AI candidate against the type-scoped list.
        _cand_norm = re.sub(r"[^a-z0-9]+", "", _ai_candidate_clean.lower())
        _cand_dedup = re.sub(r"(.)\1+", r"\1", _cand_norm)
        for _sc in allowed_subcats:
            _sc_norm = re.sub(r"[^a-z0-9]+", "", _sc.lower())
            if _sc_norm and (_sc_norm in _cand_norm or _sc_norm in _cand_dedup):
                _ai_subcategory = _sc
                break
        if not _ai_subcategory:
            # Last resort: fall back to furniture-aware normalizer for furniture/fixture.
            if asset_type in ("furniture", "fixture"):
                _ai_subcategory = normalize_furniture_subcategory(_ai_candidate, source_stem, hints)

    if _uid_subcategory:
        subcategory = _uid_subcategory
    elif _db_subcategory:
        subcategory = _db_subcategory
    else:
        subcategory = _ai_subcategory

    brand = clean_display_case(pick_with_db("brand", "Writer", "-"))
    if (not brand or brand == "-") and by_brand:
        brand = by_brand

    collection = clean_display_case(pick_with_db("collection", "Album", "-"))
    usage_location = validate_usage_location(clean_display_case(pick_with_db("usage_location", "People", "-")))
    model_name = clean_display_case(pick_with_db("model_name", "Title", "-"))
    stem_model = clean_display_case(hints.get("model", "") or hints.get("lead_desc", ""))
    # Keep a raw fallback token from the original stem (after UID prefix), preserving
    # separators like underscores for cases where that exact token is the model name.
    stem_model_raw = source_stem.strip()
    _uid_hint = (hints.get("uid", "") or "").strip()
    if _uid_hint and stem_model_raw.lower().startswith(_uid_hint.lower()):
        stem_model_raw = stem_model_raw[len(_uid_hint):].strip(" ._-")

    # Stem fallback: skip in vision-only mode (stem is likely gibberish).
    if (not model_name or model_name == "-") and enrich_mode != "vision":
        if stem_model_raw:
            model_name = stem_model_raw
        elif stem_model and stem_model != "-":
            model_name = stem_model
    size = pick_with_db("size", "Scale", "-")
    # Vendor: AI pick → DB Author → brand fallback
    vendor_name = clean_display_case(pick("vendor_name", ""))
    if not vendor_name or vendor_name == "-":
        db_vendor = db_get("Author")
        vendor_name = clean_display_case(db_vendor) if db_vendor else clean_display_case(brand)
    # Carry over Rating from DB if present
    if db_row.get("Rating", "").strip() and db_row["Rating"].strip() not in ("-", "0", ""):
        row["Rating"] = db_row["Rating"].strip()
    # Carry over URL from DB if present
    if db_row.get("URL", "").strip() and db_row["URL"].strip() not in ("-", ""):
        row["URL"] = db_row["URL"].strip()

    # Visual fields: filled by web pass, or vision pass, or both (vision wins when available).
    primary_material = "-"
    shape_form = "-"
    period = "-"
    if web_data:
        _wm = (web_data.get("primary_material_or_color", "") or "").strip()
        _ws = (web_data.get("shape_form", "") or "").strip()
        _wp = (web_data.get("period", "") or "").strip()
        if _wm and _wm != "-":
            primary_material = clean_display_case(_wm)
        if _ws and _ws != "-":
            shape_form = clean_display_case(_ws)
        if _wp and _wp != "-":
            period = clean_display_case(_wp)
    # Vision data overrides visual fields in "vision" and "both" modes.
    if vision_data:
        _vm = (vision_data.get("primary_material_or_color", "") or "").strip()
        _vs = (vision_data.get("shape_form", "") or "").strip()
        _vp = (vision_data.get("period", "") or "").strip()
        if _vm and _vm != "-":
            primary_material = clean_display_case(_vm)
        if _vs and _vs != "-":
            shape_form = clean_display_case(_vs)
        if _vp and _vp != "-":
            period = clean_display_case(_vp)

    # Post-process: reject values that look like codes, are derived from wrong fields, or are duplicated.

    # Size: only accept if an explicit dimension pattern exists directly in source_stem.
    explicit_size = re.search(r"\b\d+(?:[xX×]\d+)*\s*(?:mm|cm|m|in|ft)\b", source_stem)
    if not explicit_size:
        size = "-"

    # Model name: reject if it looks like a UID/code (only digits, hyphens, underscores, no letters > 2).
    if model_name and model_name != "-":
        letters_only = re.sub(r"[^A-Za-z]", "", model_name)
        if len(letters_only) < 3:
            model_name = "-"

    # Model name: reject if it is a very long descriptive phrase (7+ words) — likely the whole filename.
    # We allow up to 6 words to accommodate names like "Disc and Sphere Asymmetric Wall Lamp".
    if model_name and model_name != "-":
        word_count = len(model_name.split())
        if word_count >= 7:
            model_name = "-"
        else:
            # Also reject if it starts with a room/location word (descriptor, not a product name).
            # Skip this check when model_name came from the web pass — it already validated it.
            _model_from_web = bool(web_data.get("model_name", "").strip() and web_data.get("model_name") != "-")
            if not _model_from_web:
                _LOCATION_PREFIXES = {
                    "bathroom", "kitchen", "wall", "floor", "ceiling", "outdoor",
                    "wall-mounted", "wall mounted", "set", "set of",
                }
                mn_lower = model_name.lower()
                if any(mn_lower == p or mn_lower.startswith(p + " ") or mn_lower.startswith(p + "-")
                       for p in _LOCATION_PREFIXES):
                    model_name = "-"

    # Model name: strip trailing SKU codes added by vision (e.g. "FOCUS M41 31815-670" → "FOCUS M41").
    if model_name and model_name != "-":
        model_name = re.sub(r'\s+\d{3,}[-\u2013]\d{3,}(?:[-\u2013]\d+)*$', '', model_name).strip()
        if not model_name:
            model_name = "-"

    # Primary color/material: reject if it is a substring of the brand or collection name.
    if primary_material and primary_material != "-":
        pm_lower = primary_material.lower()
        if collection.lower().replace(" ", "").startswith(pm_lower.replace(" ", "")) or \
           brand.lower().startswith(pm_lower):
            primary_material = "-"

    # Remove repeated semantics across fields.
    if model_name and collection and model_name.lower() == collection.lower():
        collection = "-"
    if model_name and subcategory and sanitize_name_token(model_name).lower() == sanitize_name_token(subcategory).lower():
        model_name = "-"
    if collection and brand and collection.lower() == brand.lower():
        collection = "-"
    # Model name: strip " by <brand>" or " by <vendor>" suffix (e.g. "Luc By Rossin" → "Luc").
    if model_name and model_name != "-":
        _m_by = re.match(r'^(.+?)\s+by\s+(\w+(?:\s+\w+)?)$', model_name, re.IGNORECASE)
        if _m_by:
            _tail = _m_by.group(2).lower()
            if (brand and brand != "-" and brand.lower() == _tail) or \
               (vendor_name and vendor_name != "-" and vendor_name.lower() == _tail):
                model_name = _m_by.group(1).strip()

    # If brand field starts with the model name, strip the model prefix from it.
    # e.g. model_name="Mills", brand="Mills Minotti" → brand="Minotti"
    if model_name and model_name != "-" and brand and brand != "-":
        m_lower = model_name.lower()
        b_lower = brand.lower()
        if b_lower.startswith(m_lower + " "):
            brand = clean_display_case(brand[len(model_name):].strip()) or "-"

    # If model_name is missing but brand has exactly 2 words, the AI likely
    # concatenated product name + manufacturer into one field.
    # Heuristic: first word → model_name, second word → brand.
    # e.g. brand="Mills Minotti" → model_name="Mills", brand="Minotti"
    # EXCEPTION: skip this heuristic when brand came from the web pass — the web pass
    # already correctly separated brand from model (e.g. "Atelier Areti" is a real brand name).
    _brand_from_web = bool(web_data.get("brand", "").strip() and web_data.get("brand") != "-")
    if (not model_name or model_name == "-") and brand and brand != "-" and not _brand_from_web:
        brand_parts = brand.split()
        if len(brand_parts) == 2:
            model_name = brand_parts[0]
            brand = brand_parts[1]

    # Brand must not equal model name (or be a leading word of it) — the model likely
    # hallucinated the brand from the product name token.
    if brand and model_name and brand != "-" and model_name != "-":
        b = brand.lower()
        m = model_name.lower()
        if b == m or m.startswith(b + " ") or m.startswith(b + "-"):
            brand = "-"
    if vendor_name and model_name and vendor_name != "-" and model_name != "-":
        v = vendor_name.lower()
        m = model_name.lower()
        if v == m or m.startswith(v + " ") or m.startswith(v + "-"):
            vendor_name = "-"

    # Final safety net: if post-processing blanked model_name, keep Title populated.
    if not model_name or model_name == "-":
        for candidate in (
            stem_model_raw,
            stem_model,
            clean_display_case(hints.get("lead_desc", "")),
            brand,
            vendor_name,
        ):
            if candidate and candidate != "-":
                model_name = candidate
                break

    # ── Column writes — vary by asset_type ──────────────────────────────────
    # Extract common EFU field mapping to avoid 10+ repetitions
    def _write_efu_fields(
        subcategory_val: str,
        model_val: str,
        brand_val: str,
        collection_val: str,
        material_val: str,
        location_val: str,
        form_val: str,
        period_val: str,
        size_val: str,
        vendor_val: str,
        manager_label: str,
    ) -> None:
        """Write standardized metadata to the EFU row dict."""
        row["Subject"] = build_mood_hierarchy(subcategory_val) if subcategory_val else "-"
        row["Title"] = model_val if model_val else "-"
        row["Company"] = brand_val if brand_val else "-"
        row["Album"] = collection_val if collection_val else "-"
        row["custom_property_0"] = material_val if material_val else "-"  # Color/Material
        row["custom_property_1"] = location_val if location_val else "-"  # Location
        row["custom_property_2"] = form_val if form_val else "-"  # Form
        row["Period"] = period_val if period_val else "-"
        row["Scale"] = size_val if size_val else "-"
        row["Author"] = vendor_val if vendor_val and vendor_val != "-" else (brand_val or "-")
        cur_sourcemetadata = row.get("SourceMetadata", "-")
        if not cur_sourcemetadata or cur_sourcemetadata == "-":
            row["SourceMetadata"] = manager_label
        elif manager_label not in cur_sourcemetadata:
            row["SourceMetadata"] = f"{manager_label};{cur_sourcemetadata}"

    if asset_type == "object":
        # Object mapping (from column spec):
        # Subject=Subcategory Path, Title=Model Name, Writer=Brand, Album=Collection,
        # Genre=Primary Color/Material, People=UsageLocation, Company=Shape Form,
        # Period=Style/Period, Scale=Size, Author=VendorName
        #
        # Subcategory resolution order for object type:
        #   1. Filename prefix code (e.g. 12-11 -> Sculpture) — fully deterministic.
        #   2. Vision model output (when enrich_mode is "vision" or "both").
        #   3. hints["vision_label"] from classify_image (last resort).
        #
        # Priority 1: prefix code from filename (e.g. "12-11 object_0" -> Sculpture)
        _obj_uid_subcat = PREFIX_TO_SUBCATEGORY.get(hints.get("uid", ""), "") if hints.get("uid") else ""
        # Priority 2: vision model output
        _raw_subcat  = clean_display_case((vision_data.get("subcategory", "") or pick("subcategory", "")).strip())
        # Normalize raw label against the allowlist: handle cases like "ModernSculpture" → "Sculpture".
        def _match_allowlist(raw: str) -> str:
            if not raw or raw == "-":
                return ""
            if raw in allowed_subcats:
                return raw
            raw_spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", raw).lower()
            raw_norm = re.sub(r"[^a-z0-9]+", "", raw_spaced)
            raw_dedup = re.sub(r"(.)\1+", r"\1", raw_norm)

            # Substring match against normalized forms first.
            best = ""
            for subcat in allowed_subcats:
                sub_norm = re.sub(r"[^a-z0-9]+", "", subcat.lower())
                if not sub_norm:
                    continue
                if sub_norm in raw_norm or sub_norm in raw_dedup:
                    if len(subcat) > len(best):
                        best = subcat
            if best:
                return best

            # Fuzzy fallback for noisy/typo labels from vision (e.g. Modernscuulpture).
            norm_to_sub = {
                re.sub(r"[^a-z0-9]+", "", s.lower()): s
                for s in allowed_subcats
            }
            close = difflib.get_close_matches(raw_dedup or raw_norm, list(norm_to_sub.keys()), n=1, cutoff=0.72)
            if close:
                return norm_to_sub[close[0]]
            return best
        _obj_subcat = _match_allowlist(_raw_subcat)
        # Priority 1 wins over vision: apply prefix code if present.
        if _obj_uid_subcat and _obj_uid_subcat in allowed_subcats:
            _obj_subcat = _obj_uid_subcat
        # Final fallback: try hints["vision_label"] (from classify_image).
        if not _obj_subcat or _obj_subcat == "-":
            _obj_subcat = _match_allowlist(hints.get("vision_label", "")) or "-"
        _obj_model = clean_display_case((pick("model_name", "") or "").strip()) or "-"
        _obj_brand   = clean_display_case((vision_data.get("brand", "")      or pick("brand", "")).strip())       or "-"
        _obj_collection = clean_display_case((pick("collection", "") or "").strip()) or "-"
        _obj_mat     = clean_display_case((vision_data.get("primary_material_or_color", "") or primary_material or "-").strip()) or "-"
        _obj_form    = clean_display_case((vision_data.get("shape_form", "")  or shape_form or "-").strip())       or "-"
        _obj_period  = clean_display_case((pick("period", "") or "").strip()) or "-"
        _obj_loc     = clean_display_case((vision_data.get("usage_location", "") or usage_location or "-").strip()) or "-"
        _obj_size    = clean_display_case((vision_data.get("size", "")        or size or "-").strip())             or "-"
        _obj_vendor  = clean_display_case((vision_data.get("vendor_name", "") or vendor_name or brand or "-").strip()) or "-"
        _write_efu_fields(
            subcategory_val=_obj_subcat,
            model_val=_obj_model,
            brand_val=_obj_brand,
            collection_val=_obj_collection,
            material_val=_obj_mat,
            location_val=_obj_loc,
            form_val=_obj_form,
            period_val=_obj_period,
            size_val=_obj_size,
            vendor_val=_obj_vendor,
            manager_label="Object",
        )
    # Standardized EFU field values shared by most asset types.
    _vendor_final = vendor_name if vendor_name and vendor_name != "-" else (brand or "-")

    # Data-driven dispatch for all non-object asset types.
    # The "object" type has custom subcategory resolution logic above — kept separate.
    _MANAGER_MAP = {
        "fixture":      "Fixture",
        "vegetation":   "Vegetation",
        "people":       "People",
        "material":     "Material",
        "buildings":    "Buildings",
        "layouts":      "Layouts",
        "vehicle":      "Vehicle",
        "vfx":          "VFX",
        "procedural":   "Procedural",
        "location":     "Location",
    }

    if asset_type == "object":
        # Object mapping is handled above with dedicated subcategory resolution.
        # _write_efu_fields already called in the object block — skip re-dispatch.
        pass
    elif asset_type in _MANAGER_MAP:
        _write_efu_fields(
            subcategory_val=subcategory,
            model_val=model_name,
            brand_val=brand,
            collection_val=collection,
            material_val=primary_material,
            location_val=usage_location,
            form_val=shape_form,
            period_val=period,
            size_val=size,
            vendor_val=_vendor_final,
            manager_label=_MANAGER_MAP[asset_type],
        )
    else:
        # Generic fallback for furniture and any future asset types not yet enumerated.
        _cat_label = asset_type.capitalize() if asset_type else "Furniture"
        _write_efu_fields(
            subcategory_val=subcategory,
            model_val=model_name,
            brand_val=brand,
            collection_val=collection,
            material_val=primary_material,
            location_val=usage_location,
            form_val=shape_form,
            period_val=period,
            size_val=size,
            vendor_val=_vendor_final,
            manager_label=_cat_label,
        )

    # Keep deterministic parse as fallback and attach diagnostics non-destructively.
    diagnostics: list[str] = []
    if text_error:
        diagnostics.append(f"text_error={text_error}")
    if vision_error:
        diagnostics.append(f"vision_error={vision_error}")
    if diagnostics:
        existing = row.get("Comment", "-")
        suffix = ";" + ";".join(diagnostics)
        row["Comment"] = (existing + suffix) if existing and existing != "-" else suffix.lstrip(";")

    return row


def sanitize_name_token(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", value).strip()
    if not cleaned:
        return ""
    return "".join(part[:1].upper() + part[1:] for part in cleaned.split())


def build_short_base_name(asset_type: str, row: dict[str, str], hints: dict[str, str], fallback: str) -> str:
    mood_value = mood_hierarchy_leaf(row.get("Subject", "")) or row.get("Subject", "")
    if asset_type == "furniture":
        # Filename format: SubcategoryLeaf_ModelName_CRC32
        # Title (Model Name) is included so files are human-readable without opening the index.
        model_name_token = sanitize_name_token(row.get("Title", "") or "")
        preferred = [mood_value, model_name_token] if model_name_token and model_name_token != "-" else [mood_value]
    elif asset_type == "vegetation":
        preferred = [mood_value, row.get("Writer", "")]
    elif asset_type == "people":
        preferred = [mood_value, row.get("Writer", "")]
    elif asset_type == "material":
        preferred = [mood_value, row.get("Company", "")]
    elif asset_type == "buildings":
        preferred = [mood_value, row.get("Company", "")]
    else:
        preferred = [mood_value, row.get("People", "")]

    tokens = [sanitize_name_token(x) for x in preferred if x]
    tokens = [t for t in tokens if t]
    deterministic = "_".join(tokens) if tokens else (sanitize_name_token(fallback) or "Asset")

    # For furniture, return deterministic name directly (no Qwen cleanup needed).
    if asset_type == "furniture":
        return deterministic

    # Try Qwen cleanup first for noisy names; fallback to deterministic semantic naming.
    try:
        qwen_name = clean_name_with_qwen(
            asset_type=asset_type,
            source_stem=fallback,
            mapped_subcategory=row.get("Subject", ""),
            mapped_brand=row.get("Writer", ""),
        )
        qwen_clean = sanitize_name_token(qwen_name.replace("_", " "))
        if qwen_clean:
            return qwen_clean
    except Exception:
        pass

    return deterministic


def ensure_unique_targets(
    base_name: str,
    image_suffix: str,
    archive_suffix: str,
    image_dir: Path | None = None,
    archive_dir: Path | None = None,
) -> tuple[Path, Path, str]:
    img_dir = image_dir or THUMBNAIL_BASE
    arc_dir = archive_dir or ARCHIVE_BASE
    img_dir.mkdir(parents=True, exist_ok=True)
    arc_dir.mkdir(parents=True, exist_ok=True)
    candidate = base_name
    counter = 2
    while True:
        image_target = img_dir / f"{candidate}{image_suffix}"
        archive_target = arc_dir / f"{candidate}{archive_suffix}"
        # Keep this pure: only return available names, do not create placeholders.
        if not image_target.exists() and not archive_target.exists():
            return image_target, archive_target, candidate
        candidate = f"{base_name}_{counter}"
        counter += 1


def build_metadata_row(
    thumbnail_filename: str,
    archive_path: Path,
    asset_type: str,
    source_stem: str,
    crc32_value: str,
) -> dict[str, str]:
    hints = parse_filename_hints(source_stem)
    row: dict[str, str] = {header: "-" for header in EFU_HEADERS}
    row["Filename"] = thumbnail_filename
    row["Rating"] = "-"
    # Keep tags empty by default to avoid duplicating information already mapped
    # into dedicated columns (requested behavior).
    row["Tags"] = "-"
    row["CRC-32"] = crc32_value

    if asset_type == "furniture":
        # Furniture mapping from everything_columnmapping.md:
        # Subject=Subcategory, Title=Model Name, Writer=Brand, Album=Collection,
        # People=Usage Location, Scale=Size.
        row["Subject"] = sanitize_name_token(hints["model"] or hints["lead_desc"])
        row["Title"] = clean_display_case(hints["model"] or hints["lead_desc"])
        row["Company"] = "-"
        row["Author"] = clean_display_case(hints["brand"] or hints["brand_raw"])
        row["Album"] = clean_display_case(hints["collection"])
        row["People"] = clean_display_case(hints["lead_desc"])
        row["Scale"] = hints["size"]
        row["From"] = "-"
        row["SourceMetadata"] = "Furniture"
    elif asset_type == "vegetation":
        row["Subject"] = clean_display_case(hints["lead_desc"] or hints["model"])
        row["Company"] = hints["size"]
        row["Author"] = clean_display_case(hints["model"])
        row["Album"] = clean_display_case(hints["collection"] or hints["lead_desc"])
        row["Scale"] = hints["size"]
        row["From"] = "-"
        row["SourceMetadata"] = "Vegetation"
    elif asset_type == "people":
        row["Subject"] = clean_display_case(hints["lead_desc"])
        row["Company"] = clean_display_case(hints["model"])
        row["Author"] = clean_display_case(hints["collection"])
        row["Scale"] = hints["size"]
        row["From"] = "-"
        row["SourceMetadata"] = "People"
    elif asset_type == "material":
        row["Subject"] = clean_display_case(hints["lead_desc"] or hints["model"])
        row["Genre"] = clean_display_case(hints["collection"])
        row["Company"] = clean_display_case(hints["model"])
        row["Period"] = clean_display_case("Material Category")
        row["Scale"] = hints["size"]
        row["From"] = "-"
        row["SourceMetadata"] = "Material"
    elif asset_type == "buildings":
        row["Subject"] = clean_display_case(hints["lead_desc"])
        row["Company"] = clean_display_case(hints["model"])
        row["Period"] = clean_display_case(hints["collection"])
        row["Scale"] = hints["size"]
        row["From"] = "-"
        row["SourceMetadata"] = "Buildings"
    elif asset_type == "layouts":
        row["Subject"] = clean_display_case(hints["lead_desc"])
        row["Author"] = hints["size"]
        row["People"] = clean_display_case(hints["model"])
        row["Period"] = clean_display_case(hints["collection"])
        row["From"] = "-"
        row["SourceMetadata"] = "Layouts"
    elif asset_type == "object":
        # Object initial row: pre-populate Subject from prefix code if present,
        # otherwise leave as '-' for enrich_row_with_models to fill in.
        _init_uid = hints.get("uid", "")
        _init_subcat = PREFIX_TO_SUBCATEGORY.get(_init_uid, "") if _init_uid else ""
        row["Subject"] = build_mood_hierarchy(_init_subcat) if _init_subcat else "-"
        row["Company"] = "-"
        row["Author"] = clean_display_case(hints.get("brand", "") or hints.get("brand_raw", ""))
        row["Album"] = "-"
        row["From"] = "-"
        row["Manager"] = "Object"

    # Move source trace into the `Manager` field (Everything mapping change):
    # include parse notes / source metadata in `Manager` rather than `Comment`.
    comment_str = f"src={source_stem};crc32={crc32_value}"
    cur_manager = row.get("Manager", "-")
    if not cur_manager or cur_manager == "-":
        row["Manager"] = comment_str
    else:
        if comment_str not in cur_manager:
            row["Manager"] = f"{cur_manager};{comment_str}"
    row["Comment"] = "-"

    return row


# Fields that carry free-text display values and should be casing-normalized.
_NORMALIZE_EFU_FIELDS = {"Author", "Writer", "Album", "Genre", "People", "Company", "Period", "Scale", "Title"}


def normalize_efu_field(value: str) -> str:
    """Normalize a free-text EFU field value for uniform display:
    - Replace underscores with spaces.
    - All-alpha ALL-CAPS tokens longer than 4 chars → Title Case  (e.g. HANSGROHE → Hansgrohe).
    - Short ALL-CAPS tokens (≤4 chars) or tokens containing digits → kept as-is (codes/acronyms).
    - Mixed-case tokens (internal caps) → kept as-is (CamelCase, brand stylizations).
    - Otherwise → Title Case.
    Returns "-" unchanged.
    """
    if not value or value == "-":
        return value
    value = value.replace("_", " ").replace("-", " ").strip()
    out: list[str] = []
    for token in value.split():
        if token.isupper():
            # All-alpha ALL-CAPS token: keep only genuine short acronyms/codes (≤3 chars or contains digits).
            # 4-char brand names like FLOS, IKEA should be title-cased.
            if any(ch.isdigit() for ch in token) or len(token) <= 3:
                out.append(token)   # acronym / code: OM, WC, TY192 → keep
            else:
                out.append(token[:1].upper() + token[1:].lower())  # HANSGROHE, FLOS → Hansgrohe, Flos
        elif any(ch.isupper() for ch in token[1:]):
            out.append(token)       # mixed-case preserved: CamelCase, B&B, M41
        else:
            out.append(token[:1].upper() + token[1:].lower())
    return " ".join(out)


def normalize_efu_row(row: dict[str, str]) -> dict[str, str]:
    """Return a copy of *row* with all free-text display fields normalized."""
    out = dict(row)
    for field in _NORMALIZE_EFU_FIELDS:
        val = out.get(field, "")
        if val and val != "-":
            out[field] = normalize_efu_field(val)
    return out


def ensure_metadata_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    # If the dot-file doesn't exist but a legacy `metadata.efu` does, migrate it.
    legacy = path.parent / "metadata.efu"
    if not path.exists() and legacy.exists():
        shutil.move(str(legacy), str(path))

    # Create a fresh file if nothing exists.
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=EFU_HEADERS)
            writer.writeheader()
        return

    # Load existing rows and migrate any `Comment` src= traces into `Manager`.
    # Use utf-8-sig so BOM-prefixed headers (\ufeffFilename) are normalized.
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        existing_headers = [((h or "").lstrip("\ufeff").strip()) for h in (reader.fieldnames or [])]
        raw_rows = list(reader)

    # Normalize row keys to match stripped header names.
    rows: list[dict[str, str]] = []
    for raw in raw_rows:
        normalized: dict[str, str] = {}
        for k, v in raw.items():
            nk = (k or "").lstrip("\ufeff").strip()
            normalized[nk] = v
        rows.append(normalized)

    migrated = False
    new_rows: list[dict[str, str]] = []
    for old in rows:
        row = {k: (v if v not in (None, "") else "-") for k, v in old.items()}
        comment_val = (row.get("Comment") or "").strip()
        manager_val = (row.get("Manager") or "").strip()
        mood_val = (row.get("Mood") or "").strip()
        subject_val = (row.get("Subject") or "").strip()
        # If comment contains a src trace and manager doesn't, move it.
        if comment_val and comment_val != "-" and "src=" in comment_val and "src=" not in manager_val:
            if not manager_val or manager_val == "-":
                row["Manager"] = comment_val
            else:
                row["Manager"] = f"{manager_val};{comment_val}"
            row["Comment"] = "-"
            migrated = True
        # Migrate legacy Mood → Subject if Subject is empty/default.
        if mood_val and mood_val not in ("-",) and (not subject_val or subject_val in ("-", "")):
            mood_path = build_mood_hierarchy(mood_val)
            row["Subject"] = mood_path if mood_path and mood_path != "-" else mood_val
            migrated = True
        row = normalize_efu_row(row)
        new_rows.append(row)

    # If headers mismatch or migration happened, rewrite file with canonical headers.
    # Some historical files use an alternate schema with an `Archive` column where
    # subcategory is stored in `Subject`. Preserve data when converting back.
    is_alt_schema = "Archive" in existing_headers and "CRC-32" in existing_headers
    if existing_headers != EFU_HEADERS or migrated:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=EFU_HEADERS)
            writer.writeheader()
            for old in new_rows:
                merged = {header: "-" for header in EFU_HEADERS}
                for key, value in old.items():
                    if key in merged:
                        merged[key] = value if value not in (None, "") else "-"
                if is_alt_schema:
                    # Alternate schema: Subject=subcategory path, Archive=archive filename.
                    # Legacy schema expected by this script: Author=subcategory, Subject=archive.
                    if (not merged["Author"] or merged["Author"] == "-") and old.get("Subject"):
                        merged["Author"] = old["Subject"]
                    if (not merged["Subject"] or merged["Subject"] == "-") and old.get("Archive"):
                        merged["Subject"] = old["Archive"]
                writer.writerow(merged)


def _read_metadata_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = [((h or "").lstrip("\ufeff").strip()) for h in (reader.fieldnames or [])]
        rows = []
        for raw in reader:
            normalized: dict[str, str] = {}
            for k, v in raw.items():
                nk = (k or "").lstrip("\ufeff").strip()
                normalized[nk] = v if v not in (None, "") else "-"
            rows.append(normalized)
    return headers, rows


def _archive_name_from_row(row: dict[str, str]) -> str:
    # Support legacy and current layouts for archive filename storage.
    for key in ("Archive", "To", "Subject"):
        value = (row.get(key) or "").strip()
        if value and value != "-" and re.search(r"\.[A-Za-z0-9]{2,5}$", value):
            return value
    return ""


def find_existing_index_entry(path: Path, crc32_value: str) -> dict[str, str] | None:
    if not path.exists() or not crc32_value or crc32_value == "-":
        return None
    _, rows = _read_metadata_rows(path)
    for row in rows:
        if (row.get("CRC-32") or "").strip().upper() == crc32_value.upper():
            return row
    return None


def append_metadata_row(path: Path, row: dict[str, str], overwrite_existing: bool = False) -> None:
    ensure_metadata_file(path)
    row = normalize_efu_row(row)
    if overwrite_existing and (row.get("CRC-32") or "").strip() not in ("", "-"):
        headers, rows = _read_metadata_rows(path)
        updated = False
        for i, old in enumerate(rows):
            if (old.get("CRC-32") or "").strip().upper() == (row.get("CRC-32") or "").strip().upper():
                rows[i] = {key: row.get(key, "-") if row.get(key, "") != "" else "-" for key in EFU_HEADERS}
                updated = True
                break
        if updated:
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=EFU_HEADERS)
                writer.writeheader()
                for old in rows:
                    writer.writerow({key: old.get(key, "-") if old.get(key, "") != "" else "-" for key in EFU_HEADERS})
            return
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EFU_HEADERS)
        writer.writerow({key: row.get(key, "-") if row.get(key, "") != "" else "-" for key in EFU_HEADERS})


def preview_metadata_row(row: dict[str, str]) -> None:
    print("Metadata row preview:")
    for key in EFU_HEADERS:
        value = row.get(key, "")
        if value:
            print(f"  {key}: {value}")


def preview_mapped_metadata(asset_type: str, row: dict[str, str]) -> None:
    """Preview metadata with semantic display names for custom properties."""
    # Map technical column names to semantic display names
    display_names = {
        "Filename": "Filename",
        "Subject": "Subject",
        "Rating": "Rating",
        "Tags": "Tags",
        "URL": "URL",
        "From": "From",
        "Company": "Company",
        "Author": "Author",
        "Album": "Album",
        "custom_property_0": "Color/Material",
        "custom_property_1": "Location",
        "custom_property_2": "Form",
        "Period": "Period",
        "Scale": "Scale",
        "Title": "Title",
        "Comment": "Comment",
        "ArchiveFile": "ArchiveFile",
        "SourceMetadata": "SourceMetadata",
        "Pose": "Pose",
        "Style": "Style",
        "Content Status": "Content Status",
        "custom_property_3": "ChineseName",
        "custom_property_4": "LatinName",
        "CRC-32": "CRC-32",
    }
    
    print("Header preview:")
    preview_rows: list[tuple[str, str]] = []
    for header in EFU_HEADERS:
        display_name = display_names.get(header, header)
        preview_rows.append((display_name, row.get(header, "-") or "-"))

    name_w = max(len(name) for name, _ in preview_rows)
    val_w = max(len(value) for _, value in preview_rows)
    border = f"+{'-' * (name_w + 2)}+{'-' * (val_w + 2)}+"
    print(border)
    for name, value in preview_rows:
        print(f"| {name.ljust(name_w)} | {value.ljust(val_w)} |")
    print(border)


def confirm_apply() -> bool:
    choice = input("Proceed with rename + metadata write? [y/N]: ").strip().lower()
    return choice in {"y", "yes"}


@lru_cache(maxsize=1)
def load_clip_model():
    try:
        import torch
        import open_clip
    except ImportError as exc:
        raise ImportError(
            "CLIP scoring requires 'torch' and 'open_clip'. "
            "Install them: pip install torch open_clip_torch"
        ) from exc
    model, _, preprocess = open_clip.create_model_and_transforms(MODEL_NAME, pretrained=PRETRAINED)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device).eval()
    tokenizer = open_clip.get_tokenizer(MODEL_NAME)
    return model, preprocess, tokenizer, device


def score_labels(image_path: Path, labels: list[str]) -> tuple[str, float]:
    if not labels:
        raise ValueError("At least one label is required for CLIP scoring.")
    model, preprocess, tokenizer, device = load_clip_model()
    image = Image.open(image_path).convert("RGB")
    image_tensor = preprocess(image).unsqueeze(0).to(device)
    text_tokens = tokenizer(build_prompts(labels)).to(device)

    with torch.no_grad():
        image_features = model.encode_image(image_tensor)
        text_features = model.encode_text(text_tokens)
        image_features /= image_features.norm(dim=-1, keepdim=True)
        text_features /= text_features.norm(dim=-1, keepdim=True)
        similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)

    best_index = int(similarity.argmax().item())
    confidence = float(similarity[0, best_index].item())
    return labels[best_index], confidence


def classify_image(image_path: Path) -> tuple[str, float, str]:
    if USER_LABELS:
        user_label, user_confidence = score_labels(image_path, USER_LABELS)
        if user_confidence >= CUSTOM_LABEL_MIN_CONFIDENCE:
            return to_camel_case(user_label), user_confidence, "custom"
    # Use vision model (local Ollama or OpenRouter depending on backend)
    _label_prompt = "Return one short CamelCase product label describing the main object. No explanation."
    resp_text = ollama_generate(_label_prompt, image_path=image_path, timeout=120, spinner_label=f"Vision label: {image_path.name}")
    if not resp_text:
        raise RuntimeError("Vision model returned no label")
    return to_camel_case(resp_text.splitlines()[0]), 1.0, "qwen-vision"


def _move_with_timeout(src: str, dst: str, timeout: float = 30.0) -> Path:
    """Move a file with a timeout to prevent hanging on network drives."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(shutil.move, src, dst)
        try:
            result = future.result(timeout=timeout)
            return Path(result)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(
                f"File move timed out after {timeout}s: {src} -> {dst}. "
                "Check for locked files or network drive issues."
            )


def move_pair(
    image_path: Path,
    archive_path: Path,
    new_base_name: str,
    image_target: Path | None = None,
    archive_target: Path | None = None,
    overwrite: bool = False,
    image_dir: Path | None = None,
    archive_dir: Path | None = None,
) -> tuple[Path, Path]:
    if image_target is None or archive_target is None:
        image_target, archive_target, _ = ensure_unique_targets(
            new_base_name,
            image_path.suffix.lower(),
            archive_path.suffix.lower(),
            image_dir=image_dir,
            archive_dir=archive_dir,
        )
    if overwrite:
        # Only delete target if it is a different file from the source.
        if image_target.resolve() != image_path.resolve() and image_target.exists():
            image_target.unlink()
        if archive_target.resolve() != archive_path.resolve() and archive_target.exists():
            archive_target.unlink()
    # Skip move when source and destination are already the same file.
    if image_path.resolve() != image_target.resolve():
        moved_image = _move_with_timeout(str(image_path), str(image_target))
    else:
        moved_image = image_target
    if archive_path.resolve() != archive_target.resolve():
        moved_archive = _move_with_timeout(str(archive_path), str(archive_target))
    else:
        moved_archive = archive_target
    return moved_image, moved_archive


def main() -> None:
    try:
        # Validate all base paths before any file operations.
        _validate_base_paths()
        # Use a local variable — do NOT mutate the module-level ACTIVE_BACKEND.
        # This avoids state leakage across multiple invocations.
        _active_backend: str | None = None
        # command-line flags
        dry_run = False
        auto_yes = False
        backend: str | None = None
        asset_type: str | None = None
        # Allow non-interactive invocation with multiple file arguments (pairs)
        def process_pair(
            image_path: Path,
            archive_path: Path,
            asset_type: str,
            dry_run: bool = False,
            auto_yes: bool = False,
            session_context: str = "",
            session_hints: dict[str, str] | None = None,
        ) -> None:
            try:
                validate_inputs(image_path, archive_path)
                print(f"Processing pair: {image_path} + {archive_path}")
                hints = parse_filename_hints(image_path.stem)
                # Label: use vision classify when vision mode is active, else derive from stem.
                if vision_detect:
                    try:
                        label, confidence, label_source = classify_image(image_path)
                    except Exception as _ve_label:
                        label = to_camel_case(image_path.stem)
                        confidence = 1.0
                        label_source = "stem"
                    # Feed vision label back as a hint so enrich_row_with_models
                    # can use it as a subcategory fallback (e.g. ModernSculpture → Sculpture).
                    hints["vision_label"] = label
                else:
                    label = to_camel_case(image_path.stem)
                    confidence = 1.0
                    label_source = "stem"

                try:
                    crc32_value = compute_crc32(archive_path)
                except FileNotFoundError:
                    if dry_run:
                        crc32_value = "MISSING"
                    else:
                        raise

                # Build initial row with a placeholder filename, then derive a shorter base name
                # from mapped values so filename does not repeat metadata already captured in columns.
                # Placeholder path — real vendor-based paths are resolved after enrichment below.
                temp_archive_target = Path(f"TEMP_{crc32_value}{archive_path.suffix.lower()}")
                temp_row = build_metadata_row(
                    thumbnail_filename="",
                    archive_path=temp_archive_target,
                    asset_type=asset_type,
                    source_stem=image_path.stem,
                    crc32_value=crc32_value,
                )
                temp_row = enrich_row_with_models(
                    image_path=image_path,
                    source_stem=image_path.stem,
                    asset_type=asset_type,
                    hints=hints,
                    row=temp_row,
                    session_context=session_context,
                    session_hints=session_hints,
                    enrich_mode=enrich_mode,
                )
                # Flat output structure: put everything directly into the DB roots.
                # Do not organize by vendor for now — keep a simple flat layout.
                image_dir = THUMBNAIL_BASE
                archive_dir = ARCHIVE_BASE
                temp_archive_target = archive_dir / f"TEMP_{crc32_value}{archive_path.suffix.lower()}"

                short_base = build_short_base_name(asset_type, temp_row, hints, fallback=image_path.stem)
                short_base_with_crc = f"{short_base}_{crc32_value}"
                image_target, archive_target, new_base_name = ensure_unique_targets(
                    short_base_with_crc,
                    image_path.suffix.lower(),
                    archive_path.suffix.lower(),
                    image_dir=image_dir,
                    archive_dir=archive_dir,
                )
                overwrite_existing = False
                existing_entry = find_existing_index_entry(METADATA_EFU_PATH, crc32_value)
                if existing_entry is not None:
                    existing_img = (existing_entry.get("Filename") or "").strip()
                    existing_arc = _archive_name_from_row(existing_entry).strip()
                    if existing_img and existing_img != "-":
                        image_target = image_dir / existing_img
                    if existing_arc:
                        archive_target = archive_dir / existing_arc
                    print("WARNING: Existing index entry found for this CRC-32.")
                    print(f"  CRC-32: {crc32_value}")
                    if existing_img and existing_img != "-":
                        print(f"  Existing image: {existing_img}")
                    if existing_arc:
                        print(f"  Existing archive: {existing_arc}")
                    if auto_yes:
                        overwrite_existing = True
                        print("  --yes enabled: overwriting existing files and metadata row.")
                    else:
                        choice = input("Overwrite existing files + metadata row? [y/N]: ").strip().lower()
                        overwrite_existing = choice in {"y", "yes"}
                        if not overwrite_existing:
                            image_target, archive_target, new_base_name = ensure_unique_targets(
                                short_base_with_crc,
                                image_path.suffix.lower(),
                                archive_path.suffix.lower(),
                                image_dir=image_dir,
                                archive_dir=archive_dir,
                            )
                metadata_row = dict(temp_row)
                metadata_row["Filename"] = image_target.name
                # Keep Subject as taxonomy path; track archive filename in ArchiveFile.
                metadata_row["ArchiveFile"] = archive_target.name

                # Infer vendor from the source path by walking ancestors and skipping
                # common container folders (e.g. tmp, rar_without_zip). Use the first
                # ancestor that looks like a vendor folder.
                ignore_dirs = _kw_ignore_dirs()
                vendor_candidate = ""
                for p in image_path.parents:
                    name = p.name
                    if not name:
                        continue
                    nl = name.lower()
                    if nl in ignore_dirs or nl.startswith("."):
                        continue
                    # skip numeric-ish folders like '10-02'
                    if re.match(r"^\d{1,4}(?:[-_]\d{1,4})?$", name):
                        continue
                    vendor_candidate = name
                    break

                if not vendor_candidate:
                    vendor_candidate = image_path.parent.name or ""

                if vendor_candidate and vendor_candidate not in (".", ""):
                    vendor_clean = clean_display_case(vendor_candidate.replace("_", " ").replace("-", " "))
                    if vendor_clean:
                        metadata_row["Author"] = vendor_clean

                # Always preview (dry-run style) first.
                print(f"(preview) Label: {label} | Source: {label_source} | Confidence: {confidence:.2%}")
                print(f"(preview) CRC-32: {crc32_value}")
                print(f"(preview) Image target: {image_target}")
                print(f"(preview) Archive target: {archive_target}")
                print(f"(preview) Metadata file: {METADATA_EFU_PATH}")
                preview_mapped_metadata(asset_type, metadata_row)

                if dry_run:
                    print("(dry-run) No files were moved and no metadata was written.")
                    return

                if not auto_yes and not confirm_apply():
                    print("Skipped by user.")
                    return

                moved_image, moved_archive = move_pair(
                    image_path, archive_path, new_base_name,
                    image_target=image_target,
                    archive_target=archive_target,
                    overwrite=overwrite_existing,
                    image_dir=image_dir,
                    archive_dir=archive_dir,
                )
                append_metadata_row(METADATA_EFU_PATH, metadata_row, overwrite_existing=overwrite_existing)
                print(f"Label: {label} | Source: {label_source} | Confidence: {confidence:.2%}")
                print(f"CRC-32: {crc32_value}")
                print(f"Image moved to: {moved_image}")
                print(f"Archive moved to: {moved_archive}")
                if overwrite_existing:
                    print(f"Metadata row overwritten in: {METADATA_EFU_PATH}")
                else:
                    print(f"Metadata appended to: {METADATA_EFU_PATH}")
            except OSError as exc:
                import errno as _errno
                if exc.errno == _errno.EINVAL:
                    print(f"Skipping pair — filename contains illegal characters (e.g. \", :, ?) and cannot be opened on Windows: {image_path.name}")
                else:
                    print(f"Error processing pair {image_path} / {archive_path}: {exc}")
            except Exception as exc:
                print(f"Error processing pair {image_path} / {archive_path}: {exc}")

        # parse flags from argv
        argv = sys.argv[1:]
        # Show help table and exit if requested
        if any(a in {"-h", "--help"} for a in argv):
            _print_help_table()
            return
        # Print a compact usage reminder and a short loading screen when running interactively.
        if sys.stdout.isatty():
            show_startup_loading(duration=0.9, width=30)
            print("Usage:  python tools/ingest_asset.py --asset-type=TYPE [--backend=local|online] [--enrich-mode=text|vision|both] [--dry-run|--quick] [--yes] IMAGE ARCHIVE [IMAGE ARCHIVE ...]")
            print()
            print("  IMAGE   — path to the .jpg render  |  ARCHIVE — matching archive or 3D model file")
            print("  TYPE    — furniture | fixture | vegetation | people | material | buildings | layouts")
            print("  Options — --backend=local|online  |  --enrich-mode=text|vision|both  |  --dry-run/--quick  |  --yes")
            print()
            print("  Run with -h for full reference and examples.")
            print()
        flags = ["--dry-run"]
        clean_args: list[str] = []
        enrich_mode = "both"   # "text" | "vision" | "both"
        enrich_mode_explicit = False
        quick_alias_used = False
        unknown_options: list[str] = []
        for a in argv:
            if a in {"--dry-run", "--quick"}:
                dry_run = True
                if a == "--quick":
                    quick_alias_used = True
            elif a in {"--yes", "-y"}:
                auto_yes = True
            elif a.startswith("--backend="):
                backend = normalize_backend(a.split("=", 1)[1])
            elif a == "--online":
                backend = "online"
            elif a == "--local":
                backend = "local"
            elif a.startswith("--asset-type="):
                asset_type = normalize_asset_type(a.split("=", 1)[1])
            elif a in {"--vision-detect", "--enrich-mode=vision"}:
                enrich_mode = "vision"
                enrich_mode_explicit = True
            elif a == "--enrich-mode=both":
                enrich_mode = "both"
                enrich_mode_explicit = True
            elif a == "--enrich-mode=text":
                enrich_mode = "text"
                enrich_mode_explicit = True
            elif a.startswith("-"):
                unknown_options.append(a)
            else:
                clean_args.append(a)

        if unknown_options:
            raise ValueError(
                "Unknown option(s): " + ", ".join(unknown_options) + ". Run with -h for supported flags."
            )
        if quick_alias_used and sys.stdout.isatty():
            print("Note: --quick is treated as a legacy alias for --dry-run.")

        if backend is None:
            if sys.stdout.isatty() and not auto_yes:
                backend = prompt_backend(default_backend=ACTIVE_BACKEND)
            else:
                backend = ACTIVE_BACKEND
        _active_backend = normalize_backend(backend)
        if sys.stdout.isatty():
            print(f"Backend: {_active_backend}")

        # Enrichment mode prompt — only when interactive and not already set by flag.
        if enrich_mode == "text" and not enrich_mode_explicit and sys.stdout.isatty():
            enrich_mode = prompt_enrich_mode()

        # Derive vision_detect: enables vision for category detection + per-pair label.
        vision_detect = enrich_mode in ("vision", "both")

        if asset_type and asset_type not in ASSET_TYPES:
            raise ValueError(f"Unsupported asset type: {asset_type}")

        if asset_type == "object" and enrich_mode == "text" and not enrich_mode_explicit:
            enrich_mode = "vision"
            vision_detect = True
            if sys.stdout.isatty():
                print("Object assets default to vision enrichment; switching to vision mode.")

        if not asset_type:
            if clean_args:
                # Find the first image file in the arg list — used for vision option.
                _first_image: Path | None = next(
                    (Path(p) for p in clean_args if Path(p).suffix.lower() in IMAGE_EXTENSIONS and Path(p).exists()),
                    None,
                )
                # Mode policy:
                # - text: use filename stem detector
                # - vision: use vision detector only (ignore filename stem)
                # - both: stem first, vision refines low/medium-confidence stems
                if enrich_mode == "vision":
                    if _first_image:
                        _vis_cat, _vis_conf = detect_asset_category_vision(_first_image)
                        asset_type = _vis_cat
                        print(f"(vision-detected) asset type: {asset_type} [{_vis_conf} confidence]")
                    else:
                        asset_type = "furniture"
                        print("(vision-detected) no image found for category detection; defaulting to furniture [low confidence]")
                else:
                    # Text stem auto-detect always runs first for text/both modes.
                    _first_stem = Path(clean_args[0]).stem
                    _auto_cat, _auto_conf = detect_asset_category(_first_stem)

                    # In both mode, refine with vision when stem confidence is low/medium.
                    if enrich_mode == "both" and _first_image and _auto_conf != "high":
                        _vis_cat, _vis_conf = detect_asset_category_vision(_first_image)
                        asset_type = _vis_cat
                        print(f"(vision-detected) asset type: {asset_type} [{_vis_conf} confidence]")
                    else:
                        if sys.stdout.isatty():
                            print(f"(auto-detected) asset type: {_auto_cat} [{_auto_conf} confidence]")
                            print("  Accept? Press Enter to confirm, V to vision-scan the image, or type a category name:")
                            if _first_image:
                                print(f"  (vision will scan: {_first_image.name})")
                            _choice = input("> ").strip().lower()
                            if _choice in {"v", "vision"} and _first_image and _first_image.exists():
                                _vis_cat, _vis_conf = detect_asset_category_vision(_first_image)
                                asset_type = _vis_cat
                                print(f"(vision-detected) asset type: {asset_type} [{_vis_conf} confidence]")
                            elif _choice and _choice not in {"", "y", "yes"}:
                                _manual = normalize_asset_type(_choice)
                                asset_type = _manual if _manual in ASSET_TYPES else _auto_cat
                            else:
                                asset_type = _auto_cat
                        else:
                            asset_type = _auto_cat
                            print(f"(auto-detected) asset type: {asset_type} [{_auto_conf} confidence]")

        # Interactive session context prompt removed to reduce friction.
        # Default to no session context; parse_session_context handles empty.
        session_context = ""
        session_hints: dict[str, str] = {}

        if len(clean_args) >= 2:
            # Treat all args as a flat list of files; group by stem to find pairs.
            arg_paths = [Path(p) for p in clean_args]
            from collections import defaultdict

            stems: dict[str, list[Path]] = defaultdict(list)
            for p in arg_paths:
                stems[p.stem].append(p)

            stems_items = list(stems.items())
            total = len(stems_items)
            if total == 0:
                print("No file pairs found in arguments.")
            else:
                if sys.stdout.isatty():
                    print(f"Processing {total} pair(s)...")
                processed = 0
                for stem, items in stems_items:
                    if len(items) != 2:
                        _print_unpaired_group(stem, items, arg_paths)
                        processed += 1
                        _print_progress(processed, total)
                        continue
                    a, b = items
                    # determine which is image and which is asset/model file
                    if a.suffix.lower() in IMAGE_EXTENSIONS and b.suffix.lower() in ASSET_FILE_EXTENSIONS:
                        process_pair(a, b, asset_type=asset_type, dry_run=dry_run, auto_yes=auto_yes, session_context=session_context, session_hints=session_hints)
                    elif b.suffix.lower() in IMAGE_EXTENSIONS and a.suffix.lower() in ASSET_FILE_EXTENSIONS:
                        process_pair(b, a, asset_type=asset_type, dry_run=dry_run, auto_yes=auto_yes, session_context=session_context, session_hints=session_hints)
                    else:
                        print(f"Skipping stem '{stem}': could not identify image/asset pair ({a}, {b})")
                    processed += 1
                    _print_progress(processed, total)
        else:
            # Interactive multiline paste mode.
            # User can paste any number of file paths (one per line, mixed order),
            # then press Enter on a blank line (or Ctrl-D / Ctrl-Z) to submit.
            print()
            print("Paste file paths below (one per line). Press Enter on a blank line when done.")
            pasted_lines: list[str] = []
            try:
                while True:
                    line = input()
                    stripped = line.strip().strip('"').strip("'")
                    if not stripped:
                        break
                    pasted_lines.append(stripped)
            except EOFError:
                pass

            if not pasted_lines:
                print("No paths provided. Exiting.")
                return

            from collections import defaultdict
            valid_paste_paths: list[Path] = []
            paste_stems: dict[str, list[Path]] = defaultdict(list)
            for raw_path in pasted_lines:
                p = Path(raw_path)
                if p.exists() and p.is_file():
                    valid_paste_paths.append(p)
                    paste_stems[p.stem].append(p)
                else:
                    print(f"  Skipping (not found): {raw_path}")

            paste_items = list(paste_stems.items())
            total = len(paste_items)
            if total == 0:
                print("No valid files found in pasted paths.")
                return

            # Detect asset type from pasted paths when not supplied via --asset-type=.
            if not asset_type:
                _paste_img = next(
                    (p for p in valid_paste_paths if p.suffix.lower() in IMAGE_EXTENSIONS),
                    None,
                )
                if _paste_img:
                    if enrich_mode == "vision":
                        _vis_cat, _vis_conf = detect_asset_category_vision(_paste_img)
                        asset_type = _vis_cat
                        print(f"(vision-detected) asset type: {asset_type} [{_vis_conf} confidence]")
                    else:
                        _auto_cat, _auto_conf = detect_asset_category(_paste_img.stem)
                        if enrich_mode == "both" and _auto_conf != "high":
                            _vis_cat, _vis_conf = detect_asset_category_vision(_paste_img)
                            asset_type = _vis_cat
                            print(f"(vision-detected) asset type: {asset_type} [{_vis_conf} confidence]")
                        elif sys.stdout.isatty():
                            print(f"(auto-detected) asset type: {_auto_cat} [{_auto_conf} confidence]")
                            print("  Accept? Press Enter to confirm, V to vision-scan the image, or type a category name:")
                            _paste_choice = input("> ").strip().lower()
                            if _paste_choice in {"v", "vision"} and _paste_img.exists():
                                _vis_cat, _vis_conf = detect_asset_category_vision(_paste_img)
                                asset_type = _vis_cat
                                print(f"(vision-detected) asset type: {asset_type} [{_vis_conf} confidence]")
                            elif _paste_choice and _paste_choice not in {"", "y", "yes"}:
                                _manual = normalize_asset_type(_paste_choice)
                                asset_type = _manual if _manual in ASSET_TYPES else _auto_cat
                            else:
                                asset_type = _auto_cat
                        else:
                            asset_type = _auto_cat
                else:
                    asset_type = "furniture"

            print(f"Processing {total} pair(s)...")
            processed = 0
            for stem, items in paste_items:
                if len(items) != 2:
                    _print_unpaired_group(stem, items, valid_paste_paths, indent="  ")
                    processed += 1
                    _print_progress(processed, total)
                    continue
                a, b = items
                if a.suffix.lower() in IMAGE_EXTENSIONS and b.suffix.lower() in ASSET_FILE_EXTENSIONS:
                    process_pair(a, b, asset_type=asset_type, dry_run=dry_run, auto_yes=auto_yes, session_context=session_context, session_hints=session_hints)
                elif b.suffix.lower() in IMAGE_EXTENSIONS and a.suffix.lower() in ASSET_FILE_EXTENSIONS:
                    process_pair(b, a, asset_type=asset_type, dry_run=dry_run, auto_yes=auto_yes, session_context=session_context, session_hints=session_hints)
                else:
                    print(f"  Skipping '{stem}': could not identify image/asset pair")
                processed += 1
                _print_progress(processed, total)
    except KeyboardInterrupt:
        print("Cancelled by user.")
        sys.exit(1)
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
