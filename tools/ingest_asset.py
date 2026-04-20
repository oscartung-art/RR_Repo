from __future__ import annotations

import re
import shutil
import sys
import zlib
import concurrent.futures
import csv
import os
from functools import lru_cache
from pathlib import Path

from PIL import Image
import base64
import json
import urllib.error
import urllib.request
import threading
import time
import textwrap

THUMBNAIL_BASE = Path(r"G:\DB")
ARCHIVE_BASE = Path(r"G:\DB")
# EFU index lives in the repo regardless of where images are stored.
METADATA_EFU_PATH = Path(r"D:\RR_Repo\Database") / ".metadata.efu"
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
    # METADATA_EFU_PATH may be overridden at runtime per ingest input folder.

# Legacy move behavior is now opt-in only.
_MOVE_FILES_ENV = os.environ.get("INGEST_MOVE_FILES", "0").strip().lower()
MOVE_FILES = _MOVE_FILES_ENV in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# Column filling is documented in manual/everything_columnmapping.md.
# This script now keeps EFU column names as-is with no alias mapping layer.
# ---------------------------------------------------------------------------


def _validate_base_paths() -> None:
    """Ensure all required base directories exist before any file operations.

    Exits with a clear error message if a drive is missing or unreachable.
    """
    if not MOVE_FILES:
        return

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
# Keyword tables — embedded directly to keep this script self-contained.
# manual/ingest_keywords.md is the human-editable reference document; update
# the constants below whenever that doc changes.
# ---------------------------------------------------------------------------

# AI-only subject inference: no embedded taxonomy tables or prefix maps.

# Allowed usage-location room names.
_KW_USAGE_LOCATIONS: tuple[str, ...] = (
    "Bar",
    "Bathroom",
    "Bedroom",
    "Balcony",
    "Café",
    "Commercial",
    "Dining Room",
    "Entryway",
    "Garden",
    "Garage",
    "Gym",
    "Hallway",
    "Hotel",
    "Kids Room",
    "Kitchen",
    "Laundry",
    "Library",
    "Living Room",
    "Lobby",
    "Office",
    "Outdoor",
    "Patio",
    "Restaurant",
    "Spa",
    "Street",
    "Study",
    "Terrace",
)

# Folder names to skip during vendor path inference (matched case-insensitively).
_KW_IGNORE_DIRS: tuple[str, ...] = (
    "rar_without_zip",
    "_isolate_missing_pairs",
    "tmp",
    "temp",
    "archive",
    "unzipped",
    "images",
    "photos",
    "misc",
    "downloads",
    "3d",
)


@lru_cache(maxsize=1)
def _kw_usage_locations() -> set[str]:
    """Return the set of allowed usage-location room names."""
    return set(_KW_USAGE_LOCATIONS)


@lru_cache(maxsize=1)
def _kw_ignore_dirs() -> set[str]:
    """Return the set of folder names to skip during vendor inference."""
    return {d.lower() for d in _KW_IGNORE_DIRS}


# ---------------------------------------------------------------------------

MODEL_NAME = "ViT-L-14"
PRETRAINED = "openai"
CUSTOM_LABEL_MIN_CONFIDENCE = 0.30
# Optional online backend via OpenRouter.
_load_local_env_vars()
# Default text model for this script — Qwen 3.5 Flash is used for metadata
# extraction via OpenRouter.
# Override with OPENROUTER_MODEL env var or --model=<id> flag.
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "qwen/qwen2.5-vl-72b-instruct")
OPENROUTER_VISION_MODEL = os.environ.get("OPENROUTER_VISION_MODEL", "qwen/qwen2.5-vl-72b-instruct")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_REFERER = os.environ.get("OPENROUTER_HTTP_REFERER", "")
OPENROUTER_TITLE = os.environ.get("OPENROUTER_X_TITLE", "ingest-asset")
OPENROUTER_FALLBACK_MODELS = [
    m.strip() for m in os.environ.get(
        "OPENROUTER_FALLBACK_MODELS",
        "openai/gpt-4o-mini,qwen/qwen2.5-vl-72b-instruct,deepseek/deepseek-v3.2",
    ).split(",") if m.strip()
]
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


def _openrouter_model_candidates(preferred: str | None = None) -> list[str]:
    """Return an ordered unique list of OpenRouter models to try."""
    candidates: list[str] = []
    first = (preferred or "").strip()
    # Ignore non-provider-qualified model IDs (e.g. bare aliases).
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

EFU_HEADERS = [
    "Filename",
    "Subject",
    "Rating",
    "Tags",
    "URL",
    "Company",
    "Author",
    "Album",
    "custom_property_0",
    "custom_property_1",
    "custom_property_2",
    "Period",
    "Title",
    "Comment",
    "ArchiveFile",
    "SourceMetadata",
    "Content Status",
    "custom_property_3",
    "custom_property_4",
    "custom_property_5",
    "CRC-32",
]

# Human-friendly aliases for terminal preview output.
_PREVIEW_HEADER_ALIASES = {
    "custom_property_0": "Color",
    "custom_property_1": "Location",
    "custom_property_2": "Form",
    "custom_property_3": "ChineseName",
    "custom_property_4": "LatinName",
    "custom_property_5": "Size",
}


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
        Reads image + asset-file pairs, enriches metadata (brand, model, category)
        via AI vision + web search, moves files into G:\\DB, and appends a row
        to .metadata.efu for Everything Search.

        Usage:
            python tools/ingest_asset.py [OPTIONS] IMAGE ARCHIVE [IMAGE ARCHIVE ...]
            python tools/ingest_asset.py [OPTIONS] IMAGE              (re-enrich mode)

          IMAGE    — path to the .jpg / .png render of the asset
          ARCHIVE  — matching archive or 3D model file (same stem as IMAGE)

        Options:
          --asset-type=TYPE   Asset category (auto-detected if omitted)
                              one of: furniture | fixture | vegetation | people |
                                      material | layouts | object | vehicle | vfx
                    --nofilename        Exclude filename from AI metadata inference
          --dry-run           Preview result; no files moved, nothing written
          --quick             Alias for --dry-run
          --yes, -y           Skip confirmation prompt and apply immediately
          -h, --help          Show this help and exit

                AI models (configured in .env):
                    Text   — qwen/qwen2.5-vl-72b-instruct  (metadata extraction, web enrichment)
                    Vision — qwen/qwen2.5-vl-72b-instruct  (image analysis)
          Fallbacks — none
    """).strip())
    print()
    _print_examples()


def _print_examples() -> None:
    print(textwrap.dedent("""
        Examples:

          # Dry-run a single furniture pair (auto-detects asset type)
          python tools/ingest_asset.py --dry-run
              "G:\\DB\\10-03 mychair.jpg"
              "G:\\DB\\10-03 mychair.rar"

          # Dry-run with explicit asset type
          python tools/ingest_asset.py --dry-run --asset-type=furniture
              "G:\\DB\\10-03 mychair.jpg"
              "G:\\DB\\10-03 mychair.glb"

          # Ingest and auto-confirm (no prompt)
          python tools/ingest_asset.py --yes --asset-type=furniture
              "G:\\DB\\10-03 mychair.jpg"
              "G:\\DB\\10-03 mychair.rar"

          # Ingest multiple pairs at once
          python tools/ingest_asset.py --yes
              "G:\\DB\\10-03 mychair.jpg"  "G:\\DB\\10-03 mychair.rar"
              "G:\\DB\\10-03 mytable.jpg"  "G:\\DB\\10-03 mytable.rar"

          # Re-enrich existing thumbnails (image-only, no archive)
          python tools/ingest_asset.py --dry-run
              "G:\\DB\\Armchair_Example_4E85EE94.jpg"
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
    "material",
    "layouts",
    "fixture",
    "object",
    "vehicle",
    "vfx",
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


def build_mood_hierarchy(asset_type: str, subject_path: str) -> str:
    """Return Subject as MainCategory/... using AI-provided subject text."""
    if not subject_path or subject_path == "-":
        return "-"

    value = subject_path.strip().strip("/")
    if not value:
        return "-"

    root = (asset_type or "").strip().capitalize() or "Asset"
    if "/" not in value:
        return f"{root}/{value}"

    parts = [seg.strip() for seg in value.split("/") if seg.strip()]
    if not parts:
        return "-"
    if parts[0].lower() == root.lower():
        return "/".join(parts)
    return f"{root}/{'/'.join(parts)}"


def _subject_norm_key(value: str) -> str:
    """Normalize subject strings for tolerant matching (case/punctuation-insensitive)."""
    return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())


@lru_cache(maxsize=1)
def _load_existing_subject_index() -> tuple[dict[str, str], dict[str, str]]:
    """Load canonical Subject values from .metadata.efu for wording consistency.

    Returns:
      - full_map: normalized full-path key -> canonical full subject
      - leaf_map: normalized leaf key -> canonical full subject (unique leaves only)
    """
    full_map: dict[str, str] = {}
    leaf_candidates: dict[str, set[str]] = {}
    if not METADATA_EFU_PATH.exists():
        return full_map, {}
    try:
        with METADATA_EFU_PATH.open(encoding="utf-8", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh):
                subject = (row.get("Subject") or "").strip()
                if not subject or subject == "-":
                    continue
                full_key = _subject_norm_key(subject)
                if full_key and full_key not in full_map:
                    full_map[full_key] = subject

                leaf = mood_hierarchy_leaf(subject)
                leaf_key = _subject_norm_key(leaf)
                if leaf_key:
                    leaf_candidates.setdefault(leaf_key, set()).add(subject)
    except Exception:
        return {}, {}

    leaf_map: dict[str, str] = {}
    for key, values in leaf_candidates.items():
        if len(values) == 1:
            leaf_map[key] = next(iter(values))
    return full_map, leaf_map


def canonicalize_subject_with_metadata(candidate: str) -> str:
    """Align inferred subject wording with existing .metadata.efu Subject values."""
    value = (candidate or "").strip().strip("/")
    if not value or value == "-":
        return "-"

    full_map, leaf_map = _load_existing_subject_index()
    if not full_map and not leaf_map:
        return value

    # 1) Full-path tolerant match first.
    full_hit = full_map.get(_subject_norm_key(value), "")
    if full_hit:
        return full_hit

    # 2) Leaf match when unique in current metadata vocabulary.
    leaf = mood_hierarchy_leaf(value)
    leaf_hit = leaf_map.get(_subject_norm_key(leaf), "")
    if leaf_hit:
        return leaf_hit

    return value


def mood_hierarchy_leaf(value: str) -> str:
    """Return the terminal segment from a Mood hierarchy path."""
    if not value or value == "-":
        return ""
    return value.strip().strip("/").split("/")[-1]


def to_camel_case(label: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", label)
    if not parts:
        raise ValueError("Unable to convert an empty label into CamelCase.")
    return "".join(part[:1].upper() + part[1:] for part in parts)


def build_prompts(labels: list[str]) -> list[str]:
    return [f"a product photo of a {label}" for label in labels]


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
    if suffix in {".csv", ".txt", ".md"}:
        return "sidecar"
    return "other"


def detect_ingest_mode_from_paths(paths: list[Path], sidecar_path: Path | None = None) -> str:
    """Infer ingest mode from a flat list of pasted/CLI file paths.

    Priority:
    1) sidecar-collection when a sidecar exists with images + one archive
    2) collection when many images + one archive
    3) pairs when one image + one archive (or strict stem-pair batches)
    4) image-only when only images are provided
    5) fallback to pairs
    """
    image_count = 0
    archive_count = 0
    sidecar_count = 0
    image_stems: set[str] = set()
    archive_stems: set[str] = set()

    for p in paths:
        kind = _pair_kind(p)
        if kind == "image":
            image_count += 1
            image_stems.add(p.stem.lower())
        elif kind == "asset":
            archive_count += 1
            archive_stems.add(p.stem.lower())
        elif kind == "sidecar":
            sidecar_count += 1

    has_sidecar = (sidecar_path is not None) or (sidecar_count >= 1)
    exact_pairs = len(image_stems & archive_stems)

    if has_sidecar and image_count >= 1 and archive_count == 1:
        return "sidecar-collection"
    if image_count >= 2 and archive_count == 1:
        return "collection"
    if image_count == 1 and archive_count == 1:
        return "pairs"
    if image_count >= 1 and archive_count == 0:
        return "image-only"
    if image_count >= 1 and archive_count >= 1 and exact_pairs >= 1 and image_count == archive_count == exact_pairs:
        return "pairs"
    return "pairs"


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


def _author_from_path(path: Path) -> str:
    """Infer author/vendor from path topology.

    Preference order:
    1) first folder under THUMBNAIL_BASE / ARCHIVE_BASE (e.g. G:\\DB\\mpm\\mpmv07\\... -> mpm)
    2) immediate parent directory name as fallback
    """
    for base in (THUMBNAIL_BASE, ARCHIVE_BASE):
        try:
            rel = path.resolve().relative_to(base.resolve())
            parts = list(rel.parts)
            # parts includes filename as last segment
            if len(parts) >= 2 and parts[0].strip():
                return parts[0].strip()
        except Exception:
            continue

    parent_name = path.parent.name.strip()
    if parent_name:
        return parent_name
    return "-"


def derive_author_from_sources(paths: list[Path], sidecar_path: Path | None = None) -> str:
    """Return a deterministic author/vendor inferred from sidecar and file paths."""
    candidates: list[Path] = []
    if sidecar_path is not None and sidecar_path.exists():
        candidates.append(sidecar_path)
    candidates.extend([p for p in paths if p.exists()])

    for candidate in candidates:
        inferred = _author_from_path(candidate)
        if inferred and inferred != "-":
            return inferred
    return "-"


def resolve_metadata_efu_path_from_inputs(paths: list[Path]) -> Path:
    """Resolve .metadata.efu path from ingest inputs.

    Uses the parent folder of the first valid file path.
    Falls back to the current METADATA_EFU_PATH when no valid paths are provided.
    """
    for p in paths:
        try:
            # Prefer the provided file-like path parent even if the file is missing.
            if p.suffix:
                return p.parent / ".metadata.efu"
            if p.exists() and p.is_dir():
                return p / ".metadata.efu"
        except Exception:
            continue
    return METADATA_EFU_PATH


def set_runtime_metadata_efu_path(new_path: Path) -> None:
    """Update runtime EFU path and clear subject cache if changed."""
    global METADATA_EFU_PATH
    if METADATA_EFU_PATH.resolve() != new_path.resolve():
        METADATA_EFU_PATH = new_path
        _load_existing_subject_index.cache_clear()


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


def prompt_asset_type_choice() -> str:
    """Prompt the user to choose one asset type by number."""
    options = [
        "furniture",
        "fixture",
        "vegetation",
        "people",
        "material",
        "layouts",
        "object",
        "vehicle",
        "vfx",
    ]
    print("Select asset type:")
    for idx, name in enumerate(options, 1):
        print(f"  {idx}. {name}")
    raw = input(f"Asset type [1-{len(options)}]: ").strip()
    if not raw.isdigit():
        raise ValueError("Asset type must be entered as a number.")
    choice = int(raw)
    if choice < 1 or choice > len(options):
        raise ValueError("Invalid asset type selection number.")
    return options[choice - 1]


def detect_asset_category(stem: str) -> tuple[str, str]:
    """Auto-detect asset category from filename stem.

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
            model=OPENROUTER_MODEL,
            spinner_label="Detecting asset category...",
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
    """Use vision model to classify a 3D asset category from its render image.

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
    raw = ollama_generate(prompt, image_path=image_path, timeout=120, spinner_label="Detecting asset category...")
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
    location_list: str,
    sidecar_text: str | None = None,
) -> dict[str, str]:
    """Use the vision model to extract EFU metadata fields from a render image.

    When *sidecar_text* is supplied the model receives both the image and the
    catalogue text in a single call, which is more accurate and saves one
    round-trip compared to calling extract_sidecar_text_hints separately.

    Returns a dict with the normalized metadata keys used by the ingest pipeline (e.g. subject,
    model_name, brand, primary_material_or_color, shape_form, etc).
    """
    if sidecar_text:
        clean_text = re.sub(r'^\d+[\.)\s]\s*', '', sidecar_text.strip()).strip()
        prompt = (
            f"You are a 3D asset metadata expert for {asset_type} items. "
            "You have two sources of information about this product: "
            f'(1) Catalogue text: "{clean_text}" - use this for model_name, brand, subject, collection. '
            "(2) The attached image - use this for primary_material_or_color, shape_form, period, usage_location. "
            "Return ONLY a compact JSON object with these exact keys: "
            '"subject", "model_name", "brand", "collection", '
            '"primary_material_or_color", "usage_location", "shape_form", "period", "size", "vendor_name". '
            "STRICT rules: "
            "(1) subject must be a CamelCase hierarchy path describing what you see, "
            f"formatted as 'AssetType/Group/Leaf' (e.g. 'Furniture/Seating/Armchair', "
            f"'Fixture/Lighting/Pendant', 'Object/Decor/Book'). "
            "Main category must match the asset type. "
            f"(2) usage_location MUST be exactly one value from: {location_list}. "
            "(3) brand = manufacturer name only (e.g. 'Louis Poulsen'). "
            "    model_name = product title/model only (e.g. 'PH Snowball'). "
            "(4) Use '-' for any field you cannot confidently determine. "
            "(5) Output ONLY the JSON. No markdown, no explanation, no extra keys."
        )
        spinner_label = "Enriching from image + catalogue text..."
    else:
        prompt = (
            f"You are a 3D asset metadata expert for {asset_type} items. "
            "Look at this rendered image and return ONLY a compact JSON object with these exact keys: "
            '"subject", "model_name", "brand", "collection", '
            '"primary_material_or_color", "usage_location", "shape_form", "period", "size", "vendor_name". '
            "STRICT rules: "
            f"(1) subject must be a CamelCase hierarchy path describing what you see, "
            f"formatted as 'AssetType/Group/Leaf' (e.g. 'Furniture/Seating/Armchair', "
            f"'Fixture/Lighting/WallLamp', 'Object/Decor/Vase'). Use your best judgment. "
            f"(2) usage_location MUST be exactly one value from this list: {location_list}. "
            "(3) Use '-' for any field you cannot confidently determine from the image. "
            "(4) Output ONLY the JSON object. No markdown, no explanation, no extra keys."
        )
        spinner_label = "Extracting metadata from image..."
    raw = ollama_generate(prompt, image_path=image_path, timeout=120, spinner_label=spinner_label)
    return extract_json_payload(raw)


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

    # If the lead word is NOT a numeric prefix code (e.g. "15-09") and there is
    # no dot-separated brand field, treat the lead word as a brand hint.
    # e.g. "MORA LANTERN" → brand_hint="MORA", lead_desc="LANTERN"
    _is_prefix_code = bool(re.match(r"^\d{2}-\d{2}[A-Z]?$", lead_code))
    brand_hint = humanize(brand_clean) or (humanize(lead_code) if not _is_prefix_code and lead_code else "")

    return {
        "uid": lead_code,
        "lead_desc": humanize(lead_desc),
        "model": humanize(model_raw),
        "collection": humanize(collection_raw),
        "brand": brand_hint,
        "brand_raw": humanize(brand_raw),
        "size": size_match.group(0).replace(" ", "") if size_match else "",
        "all_text": all_text,
    }


def extract_page_key_from_stem(stem: str) -> str:
    """Extract page suffix key like p01/p102 from an image stem."""
    if not stem:
        return ""
    # Use the last pNNN token so stems like "1_mpm_vol.02_p01" resolve to p01.
    matches = re.findall(r"[pP](\d{1,3})", stem)
    if not matches:
        return ""
    match = matches[-1]
    try:
        num = int(match)
    except ValueError:
        return ""
    if num < 0:
        return ""
    # Return numeric page key without 'p' prefix (zero-padded for <100)
    return f"{num:02d}" if num < 100 else f"{num:03d}"


def _sidecar_text_line_to_page_key(line: str) -> tuple[str, str]:
    """Parse one TXT/MD sidecar line into (pXX_key, payload_text)."""
    text = (line or "").strip()
    if not text:
        return "", ""

    # Examples handled:
    #   01. Magis Chair One
    #   - 02) Magis Chair
    #   p03: Kartell chair
    m_num = re.match(r"^[\-\*\s]*([0-9]{1,3})\s*[\.:\)\-]\s*(.+)$", text)
    if m_num:
        n = int(m_num.group(1))
        # Return numeric keys without 'p' prefix. Use zero-padded 2-digit for <100.
        key = f"{n:02d}" if n < 100 else f"{n:03d}"
        return key, m_num.group(2).strip()

    m_page = re.match(r"^[\-\*\s]*[pP]([0-9]{1,3})\s*[\.:\)\-]\s*(.+)$", text)
    if m_page:
        n = int(m_page.group(1))
        key = f"{n:02d}" if n < 100 else f"{n:03d}"
        return key, m_page.group(2).strip()

    return "", ""


def _sidecar_store_entry(entries: dict[str, str], key: str, payload: str) -> None:
    """Store a sidecar entry using a normalized, case-insensitive key."""
    k = (key or "").strip().lower()
    v = (payload or "").strip()
    if not k or not v:
        return

    # Primary store under the normalized key
    entries[k] = v

    # If key is a numeric page key (e.g. '01' or '1'), store both plain and zero-padded forms.
    m_num = re.fullmatch(r"0*([0-9]{1,3})", k)
    if m_num:
        n = int(m_num.group(1))
        entries[str(n)] = v        # '1'
        entries[f"{n:02d}"] = v  # '01'
        return


def _sidecar_keys_from_filename(value: str) -> set[str]:
    """Build sidecar lookup keys from a filename/path token.

    Returns case-insensitive keys like:
      - basename with extension (e.g. "07.jpg")
      - basename stem (e.g. "07")
      - derived page key (e.g. "p07") when numeric/patterned
    """
    raw = (value or "").strip().strip('"').strip("'")
    if not raw:
        return set()

    # Accept absolute paths, relative paths, or plain names.
    try:
        name = Path(raw).name.strip()
    except Exception:
        name = raw.replace("\\", "/").split("/")[-1].strip()

    keys: set[str] = set()
    if not name:
        return keys
    keys.add(name.lower())

    stem = Path(name).stem.strip()
    if stem:
        keys.add(stem.lower())

        # Numeric stems like 7 / 07 / 007 should also map to '1' and '01' forms.
        m_num = re.fullmatch(r"0*([0-9]{1,3})", stem)
        if m_num:
            n = int(m_num.group(1))
            keys.add(str(n))
            keys.add(f"{n:02d}")

        # Also support stems already containing pNN pattern.
        page_key = extract_page_key_from_stem(stem)
        if page_key:
            # extract_page_key_from_stem now returns numeric page keys (e.g. '01')
            keys.add(page_key.lower())

    return keys


def resolve_sidecar_text_for_image(
    entries: dict[str, str],
    image_path: Path,
    page_key: str,
) -> tuple[str, str]:
    """Resolve sidecar text for one image using filename-first matching.

    Returns (payload_text, matched_key).
    """
    if not entries:
        return "", ""

    candidates: list[str] = []
    if image_path:
        candidates.append(image_path.name.lower())
        candidates.append(image_path.stem.lower())
        # Normalize purely numeric stems so 07.jpg can match key "7" and vice versa.
        m_num = re.fullmatch(r"0*([0-9]{1,3})", image_path.stem)
        if m_num:
            n = int(m_num.group(1))
            candidates.append(str(n))
            candidates.append(f"{n:02d}")

    if page_key:
        # page_key is now numeric (e.g. '01' or '1'): try both zero-padded and plain
        pk = (page_key or "").strip().lower()
        m_pk = re.fullmatch(r"0*([0-9]{1,3})", pk)
        if m_pk:
            n = int(m_pk.group(1))
            candidates.append(str(n))
            candidates.append(f"{n:02d}")
        else:
            candidates.append(pk)

    seen: set[str] = set()
    for key in candidates:
        k = (key or "").strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        text = entries.get(k, "")
        if text:
            return text, k
    # No per-entry match — fall back to full file text so the AI can figure it out.
    full = entries.get("__full__", "")
    if full:
        return full, "__full__"
    return "", ""


def parse_sidecar_entries(sidecar_path: Path) -> dict[str, str]:
    """Parse .txt/.md/.csv sidecar file into a flexible key->text map.

    Supported keys include page keys (pXX), filename (e.g. 07.jpg), and stems (e.g. 07).
    """
    entries: dict[str, str] = {}
    suffix = sidecar_path.suffix.lower()

    if suffix in {".txt", ".md"}:
        # utf-8-sig strips BOM so line "01. ..." maps correctly to p01.
        full_text = sidecar_path.read_text(encoding="utf-8-sig", errors="replace")
        for raw in full_text.splitlines():
            key, payload = _sidecar_text_line_to_page_key(raw)
            if key and payload:
                _sidecar_store_entry(entries, key, payload)
        # Always store the full text as a fallback so the AI can interpret it
        # when no per-entry key matches (e.g. messy PDF-extracted markdown).
        entries["__full__"] = full_text.strip()
        return entries

    if suffix == ".csv":
        # 1) DictReader path (headered CSV)
        try:
            with sidecar_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as fh:
                reader = csv.DictReader(fh)
                headered_rows = list(reader)
        except Exception:
            headered_rows = []

        if headered_rows:
            for row in headered_rows:
                lowered = {str(k).strip().lower(): (v or "").strip() for k, v in row.items()}
                filename_raw = ""
                for f_key in ("filename", "file", "path", "image", "image_path"):
                    filename_raw = lowered.get(f_key, "")
                    if filename_raw:
                        break

                idx_raw = ""
                for idx_key in ("index", "no", "num", "number", "page", "p"):
                    idx_raw = lowered.get(idx_key, "")
                    if idx_raw:
                        break

                page_key = ""
                if idx_raw:
                    m = re.search(r"([0-9]{1,3})", idx_raw)
                    if m:
                        n = int(m.group(1))
                        page_key = f"p{n:02d}" if n < 100 else f"p{n:03d}"

                # Prefer common description columns; fallback to joined row content.
                payload = ""
                for txt_key in ("lookup", "text", "description", "title", "name", "item", "line"):
                    payload = lowered.get(txt_key, "")
                    if payload:
                        break
                if not payload:
                    payload = " ; ".join(v for v in lowered.values() if v)

                if not payload:
                    continue

                filename_keys = _sidecar_keys_from_filename(filename_raw)
                if filename_keys:
                    for k in filename_keys:
                        _sidecar_store_entry(entries, k, payload)
                if page_key:
                    _sidecar_store_entry(entries, page_key, payload)

            if entries:
                return entries

        # 2) Fallback for non-header CSV rows like: 01, Chair text ...
        try:
            with sidecar_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as fh:
                reader2 = csv.reader(fh)
                for row in reader2:
                    if not row:
                        continue
                    first = (row[0] or "").strip()
                    payload = " ; ".join((c or "").strip() for c in row[1:] if (c or "").strip())
                    if not payload:
                        continue

                    key_added = False
                    for k in _sidecar_keys_from_filename(first):
                        _sidecar_store_entry(entries, k, payload)
                        key_added = True

                    # Numeric first column fallback (e.g. "01, Chair ...").
                    m = re.search(r"([0-9]{1,3})", first)
                    if m:
                        n = int(m.group(1))
                        page_key = f"p{n:02d}" if n < 100 else f"p{n:03d}"
                        _sidecar_store_entry(entries, page_key, payload)
                        key_added = True

                    if not key_added:
                        continue
        except Exception:
            pass

        return entries

    return entries


_SIDECAR_HINT_CACHE: dict[str, dict[str, str]] = {}


def _autodetect_archive_from_sidecar_folder(sidecar_path: Path) -> list[Path]:
    """Return archive candidates found next to sidecar file."""
    try:
        base_dir = sidecar_path.parent
        if not base_dir.exists():
            return []
        candidates = [
            p for p in base_dir.iterdir()
            if p.is_file() and p.suffix.lower() in ASSET_FILE_EXTENSIONS
        ]
        candidates.sort(key=lambda p: p.name.lower())
        return candidates
    except Exception:
        return []


def _extract_sidecar_fallback_hints(raw_text: str) -> dict[str, str]:
    """Deterministically derive basic hints from catalogue-like sidecar lines."""
    text = (raw_text or "").strip()
    if not text:
        return {}

    # Strip leading numbered list prefix: "22. ", "01. ", "1) ", etc.
    text = re.sub(r'^\d+[\.)\s]\s*', '', text).strip()

    # Drop trailing design attribution segments to isolate the product naming chunk.
    product_part = re.split(r"\bdesign\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
    product_part = product_part.strip(" .;:-")
    product_part = re.sub(r"[_\-]+", " ", product_part)
    product_part = re.sub(r"\s+", " ", product_part).strip()
    if not product_part:
        return {}

    parts = product_part.split(" ", 1)
    brand_guess = clean_display_case(parts[0]) if parts and parts[0] else ""
    model_guess = clean_display_case(parts[1]) if len(parts) > 1 else clean_display_case(product_part)

    hints: dict[str, str] = {}
    if brand_guess and brand_guess != "-":
        hints["brand"] = brand_guess
    if model_guess and model_guess != "-":
        hints["model_name"] = model_guess
    if "vendor_name" not in hints and hints.get("brand"):
        hints["vendor_name"] = hints["brand"]
    return hints


def extract_sidecar_text_hints(sidecar_text: str, location_list: str) -> dict[str, str]:
    """Convert a sidecar text snippet into normalized enrichment hints via LLM."""
    raw = (sidecar_text or "").strip()
    if not raw:
        return {}
    if raw in _SIDECAR_HINT_CACHE:
        return dict(_SIDECAR_HINT_CACHE[raw])

    # Strip leading numbered list prefix ("22. ", "01. ") before sending to AI.
    clean_raw = re.sub(r'^\d+[\.)\s]\s*', '', raw).strip()

    prompt = (
        "You are a product metadata expert for interior design assets. "
        "Extract metadata from this product catalogue text snippet. "
        "Return ONLY compact JSON with these exact keys: "
        '"subject", "model_name", "brand", "collection", '
        '"usage_location", "period", "vendor_name", "primary_material_or_color", "shape_form", "size". '
        "Rules: use '-' when unknown; no explanation; no extra keys. "
        "brand must be the manufacturer name only (e.g. 'Foscarini', 'Louis Poulsen'). "
        "model_name must be the product name/model title only (e.g. 'Le Soleil', 'PH Snowball'). "
        "subject must be a CamelCase hierarchy path describing the product, "
        "formatted as 'AssetType/Group/Leaf' (e.g. 'Fixture/Lighting/Pendant', 'Object/Decor/Book'). "
        "Main category must match the asset type implied by the text. "
        f"usage_location must be one of: {location_list}. "
        f"Text: {clean_raw}"
    )

    try:
        result = extract_json_payload(
            ollama_generate(
                prompt=prompt,
                timeout=45,
                model=OPENROUTER_VISION_MODEL,
                spinner_label="Parsing sidecar text...",
            )
        )
    except Exception:
        result = {}

    # Guarantee a useful text baseline even when model extraction is partial.
    fallback_hints = _extract_sidecar_fallback_hints(raw)
    for k, v in fallback_hints.items():
        cur = (result.get(k, "") or "").strip()
        if not cur or cur == "-":
            result[k] = v

    if result.get("usage_location"):
        result["usage_location"] = validate_usage_location(clean_display_case(result.get("usage_location", "")))

    _SIDECAR_HINT_CACHE[raw] = dict(result)
    return result


def is_descriptive_filename_stem(stem: str) -> bool:
    """Return True when a filename stem appears human-descriptive.

    Very short, mostly numeric, or random token-like stems are treated as
    non-descriptive and should not be trusted for text-first enrichment.
    """
    if not stem:
        return False
    cleaned = stem.strip().lower()
    if not cleaned:
        return False
    if re.fullmatch(r"[0-9a-f._-]+", cleaned):
        return False
    alpha_tokens = re.findall(r"[a-z]+", cleaned)
    if not alpha_tokens:
        return False
    long_tokens = [t for t in alpha_tokens if len(t) >= 4]
    if not long_tokens:
        return False
    for token in long_tokens:
        if token in {"asset", "model", "image", "photo", "render", "final", "copy"}:
            continue
        if re.search(r"[aeiou]", token):
            return True
    return False


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


def build_filename_title_fallback(source_stem: str, hints: dict[str, str]) -> str:
    """Return a deterministic Title fallback derived from the filename stem."""
    stem_model_raw = source_stem.strip()
    uid_hint = (hints.get("uid", "") or "").strip()
    if uid_hint and stem_model_raw.lower().startswith(uid_hint.lower()):
        stem_model_raw = stem_model_raw[len(uid_hint):].strip(" ._-")

    candidate = clean_display_case(stem_model_raw)
    if candidate and candidate != "-":
        return candidate
    return clean_display_case(source_stem)


def clean_name_with_qwen(asset_type: str, source_stem: str, mapped_subject: str, mapped_brand: str) -> str:
    """Use the configured LLM to clean noisy source filename into a concise semantic name."""
    prompt = (
        "Create a short clean asset filename from noisy text. "
        "Rules: remove ids/codes/checksums/numbers unless part of product model, "
        "output 1-3 words in CamelCase separated by underscore, no extension, no explanation. "
        f"Asset type: {asset_type}. Source: {source_stem}. "
        f"Subject hint: {mapped_subject}. Brand hint: {mapped_brand}."
    )
    text = ollama_generate(
        prompt=prompt,
        timeout=45,
        spinner_label="Normalising product name...",
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
        spinner_msg = spinner_label or f"Vision: extracting from {_vision_model.split('/')[-1]}..."
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

    spinner_msg = spinner_label or "Waiting for AI response..."
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


def infer_metadata_fields(
    asset_type: str,
    source_stem: str,
    image_path: Path | None = None,
    sidecar_text: str | None = None,
    use_filename_signal: bool = True,
) -> dict[str, str]:
    """Single AI call to extract all metadata fields.

    Trust order (default): asset_type > sidecar text > filename > image.
    Returns a dict with keys: subject, model_name, brand, collection,
    primary_material_or_color, usage_location, shape_form, period, size, vendor_name.
    """
    location_list = ", ".join(sorted(USAGE_LOCATION_ROOMS))

    prompt = (
        f"You are a 3D asset metadata expert. The asset type is {asset_type}.\n"
        "You have these information sources in trust order:\n"
        f"1. Asset type: {asset_type} (always correct)\n"
    )
    trust_index = 2
    if sidecar_text and sidecar_text.strip():
        clean = re.sub(r'^\d+[\.\)\s]\s*', '', sidecar_text.strip()).strip()
        prompt += f'{trust_index}. Catalogue/sidecar text: "{clean}" (authoritative when available)\n'
        trust_index += 1
    if use_filename_signal:
        prompt += (
            f"{trust_index}. Filename stem: '{source_stem}' "
            "(strong indicator when it contains recognizable product/brand tokens)\n"
        )
        trust_index += 1
    prompt += f"{trust_index}. The attached image (accurate but may have ambiguity)\n\n"
    prompt += (
        "Return ONLY a compact JSON object with these exact keys:\n"
        '"subject", "model_name", "brand", "collection", '
        '"primary_material_or_color", "usage_location", "shape_form", '
        '"period", "size", "vendor_name".\n'
        "Rules:\n"
        "- subject: one short subcategory phrase (Title Case, spaces, no root category prefix). "
        "Examples: Outdoor Lounge Furniture, Pendant Lighting, Decorative Vase.\n"
        "- model_name: product name/model title only (e.g. 'PH Snowball', 'Zenith Lounger').\n"
        "- brand: manufacturer name only (e.g. 'Gloster', 'Louis Poulsen').\n"
        f"- usage_location: one value from: {location_list}.\n"
        "- Use '-' for any field you cannot confidently determine.\n"
        "- No markdown, no explanation, no extra keys."
    )

    try:
        raw = ollama_generate(
            prompt=prompt,
            image_path=image_path if image_path and image_path.exists() else None,
            timeout=120,
            model=OPENROUTER_VISION_MODEL,
            spinner_label="Extracting metadata...",
        )
        return extract_json_payload(raw)
    except Exception:
        return {}


def _clean_field(fields: dict[str, str], key: str) -> str:
    """Extract, strip, and display-case normalize one field from AI output."""
    val = (fields.get(key, "") or "").strip().strip('"').strip("'")
    if not val or val == "-":
        return "-"
    # Strip code fences / root-category prefix for subject.
    val = re.sub(r"^`+|`+$", "", val).strip()
    return clean_display_case(val) or "-"


# Web enrichment was removed by policy. Metadata sources are now limited to:
# AI model output and sidecar text.


def enrich_row_with_models(
    image_path: Path,
    source_stem: str,
    asset_type: str,
    hints: dict[str, str],
    row: dict[str, str],
    session_context: str = "",
    session_hints: dict[str, str] | None = None,
    vision_only: bool = False,
    text_hint_override: dict[str, str] | None = None,
    disable_web_search: bool = False,
    raw_sidecar_text: str | None = None,
    use_filename_signal: bool = True,
) -> dict[str, str]:
    """Metadata enrichment pipeline.

    Single AI call with trust order: asset_type > sidecar text > filename > image.
    All AI-induced fields come directly from the model output.
    """

    # Merge any text_hint_override into sidecar text so the AI sees it.
    effective_sidecar = (raw_sidecar_text or "").strip()
    if text_hint_override:
        extra = "; ".join(
            f"{k}: {v}" for k, v in text_hint_override.items()
            if (v or "").strip() and v.strip() != "-"
        )
        if extra:
            effective_sidecar = f"{effective_sidecar}\n{extra}".strip() if effective_sidecar else extra

    print(f"  Reading image: {image_path.name}", flush=True)
    fields = infer_metadata_fields(
        asset_type=asset_type,
        source_stem=source_stem,
        image_path=image_path if image_path.exists() else None,
        sidecar_text=effective_sidecar or None,
        use_filename_signal=use_filename_signal,
    )

    # ── Extract and normalize all AI fields ──────────────────────────────
    subject_path  = _clean_field(fields, "subject")
    model_name    = _clean_field(fields, "model_name")
    brand         = _clean_field(fields, "brand")
    collection    = _clean_field(fields, "collection")
    primary_material = _clean_field(fields, "primary_material_or_color")
    usage_location = validate_usage_location(_clean_field(fields, "usage_location"))
    shape_form    = _clean_field(fields, "shape_form")
    period        = _clean_field(fields, "period")
    size          = _clean_field(fields, "size")
    vendor_name   = _clean_field(fields, "vendor_name")

    # Vendor defaults to brand when AI leaves it blank.
    if vendor_name == "-" and brand != "-":
        vendor_name = brand

    # Strip root-category prefix from subject so build_mood_hierarchy can add it back.
    if subject_path != "-":
        root = (asset_type or "").strip().lower()
        sp = subject_path.strip().strip("/")
        if sp.lower().startswith(root + "/"):
            sp = sp[len(root) + 1:].strip().strip("/")
        # Keep only the leaf phrase when the model returns a multi-level path.
        if "/" in sp:
            sp = sp.split("/")[-1]
        sp = re.sub(r"[_\-]+", " ", sp)
        sp = re.sub(r"[^A-Za-z0-9\s]", "", sp)
        sp = re.sub(r"\s+", " ", sp).strip()
        subject_path = clean_display_case(sp) if sp else "-"

    # Carry over deterministic fields from CurrentDB when available.
    db_row = lookup_current_db(source_stem)
    if db_row.get("Rating", "").strip() and db_row["Rating"].strip() not in ("-", "0", ""):
        row["Rating"] = db_row["Rating"].strip()
    if db_row.get("URL", "").strip() and db_row["URL"].strip() not in ("-", ""):
        row["URL"] = db_row["URL"].strip()

    # ── Write to EFU row ─────────────────────────────────────────────────
    row["Subject"] = build_mood_hierarchy(asset_type, subject_path) if subject_path != "-" else "-"
    row["Title"] = model_name
    row["Company"] = brand
    row["Album"] = collection
    row["custom_property_0"] = primary_material
    row["custom_property_1"] = usage_location
    row["custom_property_2"] = shape_form
    row["Period"] = period
    row["custom_property_5"] = size
    row["Author"] = vendor_name if vendor_name != "-" else (brand if brand != "-" else "-")

    return row


def sanitize_name_token(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", value).strip()
    if not cleaned:
        return ""
    return "".join(part[:1].upper() + part[1:] for part in cleaned.split())


def build_short_base_name(asset_type: str, row: dict[str, str], hints: dict[str, str], fallback: str) -> str:
    mood_value = mood_hierarchy_leaf(row.get("Subject", "")) or row.get("Subject", "")
    if asset_type == "furniture":
        # Filename format: SubjectLeaf_ModelName_CRC32
        # Title is included so files are human-readable without opening the index.
        model_name_token = sanitize_name_token(row.get("Title", "") or "")
        preferred = [mood_value, model_name_token] if model_name_token and model_name_token != "-" else [mood_value]
    elif asset_type == "fixture":
        # Filename format: SubjectLeaf_ModelName_CRC32
        model_name_token = sanitize_name_token(row.get("Title", "") or "")
        preferred = [p for p in [mood_value, model_name_token] if p and p != "-"]
    elif asset_type == "vegetation":
        preferred = [mood_value, row.get("Author", "")]
    elif asset_type == "people":
        preferred = [mood_value, row.get("Author", "")]
    elif asset_type == "material":
        preferred = [mood_value, row.get("Company", "")]
    elif asset_type == "buildings":
        preferred = [mood_value, row.get("Company", "")]
    else:
        preferred = [mood_value, row.get("custom_property_1", "")]

    tokens = [sanitize_name_token(x) for x in preferred if x]
    tokens = [t for t in tokens if t]
    deterministic = "_".join(tokens) if tokens else (sanitize_name_token(fallback) or "Asset")

    # For furniture and fixture, return deterministic name directly (no Qwen cleanup needed).
    if asset_type in ("furniture", "fixture"):
        return deterministic

    # Try Qwen cleanup first for noisy names; fallback to deterministic semantic naming.
    try:
        qwen_name = clean_name_with_qwen(
            asset_type=asset_type,
            source_stem=fallback,
            mapped_subject=row.get("Subject", ""),
            mapped_brand=row.get("Company", ""),
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
        row["Title"] = clean_display_case(hints["model"] or hints["lead_desc"])
        row["Company"] = "-"
        row["Author"] = clean_display_case(hints["brand"] or hints["brand_raw"])
        row["Album"] = clean_display_case(hints["collection"])
        row["custom_property_5"] = hints["size"]
    elif asset_type == "vegetation":
        row["Company"] = hints["size"]
        row["Author"] = clean_display_case(hints["model"])
        row["Album"] = clean_display_case(hints["collection"] or hints["lead_desc"])
        row["custom_property_5"] = hints["size"]
    elif asset_type == "people":
        row["Company"] = clean_display_case(hints["model"])
        row["Author"] = clean_display_case(hints["collection"])
        row["custom_property_5"] = hints["size"]
    elif asset_type == "material":
        row["Album"] = clean_display_case(hints["collection"])
        row["Company"] = clean_display_case(hints["model"])
        row["Period"] = clean_display_case("Material Category")
        row["custom_property_5"] = hints["size"]
    elif asset_type == "buildings":
        row["Company"] = clean_display_case(hints["model"])
        row["Period"] = clean_display_case(hints["collection"])
        row["custom_property_5"] = hints["size"]
    elif asset_type == "layouts":
        row["Title"] = clean_display_case(hints["model"])
        row["Period"] = clean_display_case(hints["collection"])
        row["custom_property_5"] = hints["size"]
    elif asset_type == "object":
        # Subject stays unset until AI enrichment fills it.
        row["Company"] = "-"
        row["Author"] = clean_display_case(hints.get("brand", "") or hints.get("brand_raw", ""))
        row["Album"] = "-"
    row["Comment"] = "-"

    return row


# Fields that carry free-text display values and should be casing-normalized.
_NORMALIZE_EFU_FIELDS = {
    "Author", "Album", "Company", "Period", "Title",
    "custom_property_0", "custom_property_1", "custom_property_2",
    "custom_property_3", "custom_property_4", "custom_property_5",
}


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

    # Load existing rows and migrate legacy columns into the canonical schema.
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
        source_meta_val = (row.get("SourceMetadata") or "").strip()
        scale_val = (row.get("Scale") or "").strip()
        cp5_val = (row.get("custom_property_5") or "").strip()
        mood_val = (row.get("Mood") or "").strip()
        subject_val = (row.get("Subject") or "").strip()
        # If comment contains a src trace, keep it in SourceMetadata (not Manager).
        if comment_val and comment_val != "-" and "src=" in comment_val and "src=" not in source_meta_val:
            if not source_meta_val or source_meta_val == "-":
                row["SourceMetadata"] = comment_val
            else:
                row["SourceMetadata"] = f"{source_meta_val};{comment_val}"
            row["Comment"] = "-"
            migrated = True
        # If legacy Manager has source trace, merge it into SourceMetadata.
        if manager_val and manager_val != "-" and "src=" in manager_val:
            new_source = (row.get("SourceMetadata") or "-").strip()
            if not new_source or new_source == "-":
                row["SourceMetadata"] = manager_val
                migrated = True
            elif manager_val not in new_source:
                row["SourceMetadata"] = f"{new_source};{manager_val}"
                migrated = True
        # Legacy Scale column migrated to canonical Size column.
        if (not cp5_val or cp5_val == "-") and scale_val and scale_val != "-":
            row["custom_property_5"] = scale_val
            migrated = True
        # Migrate legacy Mood → Subject if Subject is empty/default.
        if mood_val and mood_val not in ("-",) and (not subject_val or subject_val in ("-", "")):
            row["Subject"] = mood_val
            migrated = True
        row = normalize_efu_row(row)
        new_rows.append(row)

    # If headers mismatch or migration happened, rewrite file with canonical headers.
    # Some historical files use an alternate schema with an `Archive` column where
    # subject path is stored in `Subject`. Preserve data when converting back.
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
                    # Alternate schema: Subject=subject path, Archive=archive filename.
                    # Legacy schema expected by this script: Author=subject path, Subject=archive.
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


def find_existing_index_entry_by_filename(path: Path, filename: str) -> dict[str, str] | None:
    """Find metadata entry by thumbnail filename (for re-enrichment mode).

    Compares by basename only so the lookup works whether Filename is stored
    as a bare name (legacy) or an absolute path (new style).
    """
    if not path.exists() or not filename or filename == "-":
        return None
    query_name = Path(filename).name.strip().lower()
    _, rows = _read_metadata_rows(path)
    for row in rows:
        stored = (row.get("Filename") or "").strip()
        if Path(stored).name.lower() == query_name:
            return row
    return None


def append_metadata_row(path: Path, row: dict[str, str], overwrite_existing: bool = False, overwrite_by_filename: str = "") -> None:
    ensure_metadata_file(path)
    row = normalize_efu_row(row)
    # Collection mode: match the old entry by its original filename, not CRC,
    # because all images in a collection share the same archive CRC.
    if overwrite_by_filename:
        query_name = Path(overwrite_by_filename).name.strip().lower()
        headers, rows = _read_metadata_rows(path)
        updated = False
        for i, old in enumerate(rows):
            stored = (old.get("Filename") or "").strip()
            if Path(stored).name.lower() == query_name:
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


def preview_mapped_metadata(asset_type: str, row: dict[str, str]) -> None:
    """Preview metadata using human-friendly aliases for custom properties."""

    print("Header preview:")
    preview_rows: list[tuple[str, str]] = []
    for header in EFU_HEADERS:
        value = (row.get(header, "") or "").strip()
        if not value or value == "-":
            continue
        display_name = _PREVIEW_HEADER_ALIASES.get(header, header)
        preview_rows.append((display_name, value))

    if not preview_rows:
        print("  (no enriched fields)")
        return

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


def confirm_apply_all(total: int, label: str = "item(s)") -> bool:
    choice = input(f"Proceed with rename + metadata write for all {total} {label}? [y/N]: ").strip().lower()
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
    import torch

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
    # Use vision model
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


def process_reenrich(
    image_path: Path,
    asset_type: str,
    dry_run: bool = False,
    auto_yes: bool = False,
    session_context: str = "",
    session_hints: dict[str, str] | None = None,
    vision_only: bool = False,
    use_filename_signal: bool = True,
) -> None:
    """Re-enrich an existing thumbnail: lookup metadata entry by filename and update it.
    
    Used when you have already ingested an image and want to run enrichment again
    to get further vision-based enrichment without requiring the archive file.
    """
    try:
        if not image_path.exists():
            print(f"  Image not found: {image_path}")
            return
        
        if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            print(f"  Not an image file (unsupported extension): {image_path.name}")
            return
        
        # Find existing entry by filename
        existing_entry = find_existing_index_entry_by_filename(METADATA_EFU_PATH, image_path.name)
        if existing_entry is None:
            print(f"  No existing index entry found for: {image_path.name}")
            print(f"    (Check that the file is already in the metadata index)")
            return
        
        crc32_value = (existing_entry.get("CRC-32") or "").strip()
        if not crc32_value or crc32_value == "-":
            print(f"  Cannot re-enrich: existing entry has no CRC-32 value for {image_path.name}")
            return
        
        print(f"Re-enriching: {image_path.name}")
        
        # Parse any hints from the filename
        hints = parse_filename_hints(image_path.stem)
        
        # Vision label detection
        try:
            label, confidence, label_source = classify_image(image_path)
            hints["vision_label"] = label
            hints["vision_confidence"] = f"{confidence:.6f}"
        except Exception:
            label = to_camel_case(image_path.stem)
            confidence = 0.0
            label_source = "stem"
            hints["vision_label"] = label
            hints["vision_confidence"] = "0.0"
        
        # Build initial metadata row from existing entry
        metadata_row = dict(existing_entry)
        
        # Re-enrich with models (this is the key step for further enrichment)
        metadata_row = enrich_row_with_models(
            image_path=image_path,
            source_stem=image_path.stem,
            asset_type=asset_type,
            hints=hints,
            row=metadata_row,
            session_context=session_context,
            session_hints=session_hints,
            vision_only=vision_only,
            use_filename_signal=use_filename_signal,
        )
        
        # Preview the updated metadata
        print(f"(preview) Label: {label} | Source: {label_source} | Confidence: {confidence:.2%}")
        print(f"(preview) CRC-32: {crc32_value}")
        preview_mapped_metadata(asset_type, metadata_row)
        
        if dry_run:
            print("(dry-run) No metadata was updated.")
            return
        
        if not auto_yes and not confirm_apply():
            print("Skipped by user.")
            return
        
        # Update metadata in the index (overwrite existing entry)
        append_metadata_row(METADATA_EFU_PATH, metadata_row, overwrite_existing=True)
        print(f"Label: {label} | Source: {label_source} | Confidence: {confidence:.2%}")
        print(f"CRC-32: {crc32_value}")
        print(f"Metadata updated in: {METADATA_EFU_PATH}")
        
    except Exception as exc:
        print(f"Error re-enriching {image_path}: {exc}")


def _classify_image_with_fallback(
    image_path: Path,
    hints: dict[str, str],
) -> tuple[str, float, str]:
    """Classify an image and store a stable fallback label hint."""
    try:
        label, confidence, label_source = classify_image(image_path)
        hints["vision_label"] = label
        hints["vision_confidence"] = f"{confidence:.6f}"
    except Exception:
        label = to_camel_case(image_path.stem)
        confidence = 0.0
        label_source = "stem"
        hints["vision_label"] = label
        hints["vision_confidence"] = "0.0"
    return label, confidence, label_source


def _build_enriched_image_row(
    image_path: Path,
    asset_type: str,
    crc32_value: str,
    archive_file_name: str,
    hints: dict[str, str],
    session_context: str,
    session_hints: dict[str, str] | None,
    author_input: str,
    vision_only: bool = False,
    text_hint_override: dict[str, str] | None = None,
    disable_web_search: bool = False,
    raw_sidecar_text: str | None = None,
    use_filename_signal: bool = True,
) -> dict[str, str]:
    """Build and enrich one image metadata row with shared ingestion behavior."""
    temp_row = build_metadata_row(
        thumbnail_filename="",
        archive_path=Path("-"),
        asset_type=asset_type,
        source_stem=image_path.stem,
        crc32_value=crc32_value,
    )
    if author_input:
        temp_row["Author"] = author_input
    temp_row = enrich_row_with_models(
        image_path=image_path,
        source_stem=image_path.stem,
        asset_type=asset_type,
        hints=hints,
        row=temp_row,
        session_context=session_context,
        session_hints=session_hints,
        vision_only=vision_only,
        text_hint_override=text_hint_override,
        disable_web_search=disable_web_search,
        raw_sidecar_text=raw_sidecar_text,
        use_filename_signal=use_filename_signal,
    )
    if author_input:
        temp_row["Author"] = author_input
    temp_row["ArchiveFile"] = archive_file_name
    return temp_row


def _make_unique_image_target(
    image_path: Path,
    short_base_with_crc: str,
    image_dir: Path,
) -> Path:
    """Return a unique image target path, preserving current-file identity."""
    suffix = image_path.suffix.lower()
    image_target = image_dir / f"{short_base_with_crc}{suffix}"
    counter = 1
    while image_target.exists() and image_target.resolve() != image_path.resolve():
        image_target = image_dir / f"{short_base_with_crc}_{counter:02d}{suffix}"
        counter += 1
    return image_target


def process_image_only(
    image_path: Path,
    asset_type: str,
    dry_run: bool = False,
    auto_yes: bool = False,
    session_context: str = "",
    session_hints: dict[str, str] | None = None,
    author_input: str = "",
    vision_only: bool = False,
    use_filename_signal: bool = True,
) -> None:
    """Ingest a standalone image with no archive.

    CRC-32 is computed from the image itself.  A new EFU row is created with
    ArchiveFile set to '-'.  The image is moved to THUMBNAIL_BASE.
    """
    try:
        if not image_path.exists():
            print(f"  Image not found: {image_path}")
            return
        if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            print(f"  Not an image file: {image_path.name}")
            return

        print(f"Processing image-only: {image_path}")
        hints = parse_filename_hints(image_path.stem)
        label, confidence, label_source = _classify_image_with_fallback(image_path, hints)

        if dry_run:
            crc32_value = f"DRY_{image_path.stem[:8].upper()}"
        else:
            crc32_value = compute_crc32(image_path)

        temp_row = _build_enriched_image_row(
            image_path=image_path,
            asset_type=asset_type,
            crc32_value=crc32_value,
            archive_file_name="-",
            hints=hints,
            session_context=session_context,
            session_hints=session_hints,
            author_input=author_input,
            vision_only=vision_only,
            use_filename_signal=use_filename_signal,
        )

        # Build image target path inside THUMBNAIL_BASE.
        image_dir = image_path.parent
        short_base = build_short_base_name(asset_type, temp_row, hints, fallback=image_path.stem)
        short_base_with_crc = f"{short_base}_{crc32_value}"
        image_target = _make_unique_image_target(image_path, short_base_with_crc, image_dir)

        overwrite_existing = False
        existing_entry = find_existing_index_entry(METADATA_EFU_PATH, crc32_value)
        if existing_entry is not None:
            existing_img = (existing_entry.get("Filename") or "").strip()
            if existing_img and existing_img != "-":
                _existing_p = Path(existing_img)
                image_target = _existing_p if _existing_p.is_absolute() else image_dir / existing_img
            print("WARNING: Existing index entry found for this CRC-32.")
            print(f"  CRC-32: {crc32_value}")
            if existing_img and existing_img != "-":
                print(f"  Existing image: {existing_img}")
            if auto_yes:
                overwrite_existing = True
                print("  --yes enabled: overwriting existing files and metadata row.")
            else:
                choice = input("Overwrite existing entry? [y/N]: ").strip().lower()
                overwrite_existing = choice in {"y", "yes"}
                if not overwrite_existing:
                    image_target = _make_unique_image_target(image_path, short_base_with_crc, image_dir)

        metadata_row = dict(temp_row)
        metadata_row["Filename"] = image_target.name
        metadata_row["ArchiveFile"] = "-"

        print(f"(preview) Label: {label} | Source: {label_source} | Confidence: {confidence:.2%}")
        print(f"(preview) CRC-32: {crc32_value}")
        print(f"(preview) Image target: {image_target}")
        print(f"(preview) Metadata file: {METADATA_EFU_PATH}")
        preview_mapped_metadata(asset_type, metadata_row)

        if dry_run:
            print("(dry-run) No files were moved and no metadata was written.")
            return

        if not auto_yes and not confirm_apply():
            print("Skipped by user.")
            return

        if overwrite_existing and image_target.exists() and image_target.resolve() != image_path.resolve():
            image_target.unlink()
        if image_path.resolve() != image_target.resolve():
            moved_image = _move_with_timeout(str(image_path), str(image_target))
        else:
            moved_image = image_target

        append_metadata_row(METADATA_EFU_PATH, metadata_row, overwrite_existing=overwrite_existing)
        print(f"Label: {label} | Source: {label_source} | Confidence: {confidence:.2%}")
        print(f"CRC-32: {crc32_value}")
        print(f"Image renamed to: {moved_image}")
        if overwrite_existing:
            print(f"Metadata row overwritten in: {METADATA_EFU_PATH}")
        else:
            print(f"Metadata appended to: {METADATA_EFU_PATH}")

    except OSError as exc:
        import errno as _errno
        if exc.errno == _errno.EINVAL:
            print(f"Skipping — filename contains illegal characters: {image_path.name}")
        else:
            print(f"Error processing image-only {image_path}: {exc}")
    except Exception as exc:
        print(f"Error processing image-only {image_path}: {exc}")


def _show_sidecar_collection_preview(
    images: list,
    sidecar_entries: dict,
    archive_crc32: str,
    archive_file_name: str,
    asset_type: str,
    session_context: str = "",
    session_hints: dict[str, str] | None = None,
    author_input: str = "",
    vision_only: bool = False,
    dry_run: bool = False,
    auto_yes: bool = False,
) -> "dict[str, tuple] | None":
    """Run combined vision+text enrichment for every image, print a preview table,
    and ask the user to confirm before the write loop begins.

    Returns a dict mapping str(image_path) -> (temp_row, label, confidence, label_source)
    so the write loop can reuse the results without a second API call.
    Returns None if the user aborts (or dry_run).
    """
    SEP = "  "
    cache: dict[str, tuple] = {}

    print()
    print(f"Running enrichment preview for {len(images)} image(s)…")
    for i, img_path in enumerate(images, 1):
        page_key = extract_page_key_from_stem(img_path.stem)
        sidecar_text, matched_key = resolve_sidecar_text_for_image(sidecar_entries, img_path, page_key)
        if sidecar_text:
            print(f"  [{i}/{len(images)}] {img_path.name} → sidecar: {matched_key}")
        else:
            print(f"  [{i}/{len(images)}] {img_path.name} → no sidecar match (vision only)")

        hints = parse_filename_hints(img_path.stem)
        label, confidence, label_source = _classify_image_with_fallback(img_path, hints)
        temp_row = _build_enriched_image_row(
            image_path=img_path,
            asset_type=asset_type,
            crc32_value=archive_crc32,
            archive_file_name=archive_file_name,
            hints=hints,
            session_context=session_context,
            session_hints=session_hints,
            author_input=author_input,
            vision_only=vision_only,
            text_hint_override=None,
            disable_web_search=True,
            raw_sidecar_text=sidecar_text if sidecar_text else None,
        )
        collection_album = img_path.parent.name.strip()
        if collection_album:
            temp_row["Album"] = collection_album
        short_base = build_short_base_name(asset_type, temp_row, hints, fallback=img_path.stem)
        predicted_name = f"{short_base}_{archive_crc32}{img_path.suffix.lower()}"
        cache[str(img_path)] = (temp_row, label, confidence, label_source, predicted_name)

    # Build table rows
    table_rows = []
    for i, img_path in enumerate(images, 1):
        entry = cache[str(img_path)]
        temp_row, label, confidence, label_source, predicted_name = entry
        table_rows.append((
            str(i),
            img_path.name,
            temp_row.get("Subject", "-") or "-",
            temp_row.get("Title", "-") or "-",
            temp_row.get("Company", "-") or "-",
            temp_row.get("custom_property_0", "-") or "-",
            temp_row.get("custom_property_1", "-") or "-",
            predicted_name,
        ))

    headers = ("#", "Original File", "Subject", "Title", "Brand", "Color", "Location", "Predicted New Name")
    widths = [
        max(len(headers[j]), *(len(r[j]) for r in table_rows))
        for j in range(len(headers))
    ]
    total_width = sum(widths) + len(SEP) * (len(widths) - 1)

    header_line = SEP.join(h.ljust(w) for h, w in zip(headers, widths))
    divider = SEP.join("-" * w for w in widths)

    print()
    print("━" * total_width)
    print("  SIDECAR COLLECTION PREVIEW")
    print("━" * total_width)
    print(header_line)
    print(divider)
    for row in table_rows:
        print(SEP.join(v.ljust(w) for v, w in zip(row, widths)))
    print()

    if dry_run:
        print("(dry-run) Preview complete — no files moved, no metadata written.")
        return None

    if auto_yes:
        return cache

    answer = input(f"Proceed with rename + metadata write for all {len(images)} image(s)? [y/N]: ").strip().lower()
    if answer not in ("y", "yes"):
        print("Aborted by user.")
        return None
    return cache


def process_collection_image(
    image_path: Path,
    archive_crc32: str,
    archive_file_name: str,
    asset_type: str,
    dry_run: bool = False,
    auto_yes: bool = False,
    session_context: str = "",
    session_hints: dict[str, str] | None = None,
    author_input: str = "",
    vision_only: bool = False,
    sidecar_text: str = "",
    disable_web_search: bool = False,
    precomputed: "tuple | None" = None,
    use_filename_signal: bool = True,
) -> None:
    """Ingest one image from a collection that shares a single archive.

    The archive has already been moved to ARCHIVE_BASE and its CRC-32 is
    pre-computed.  This function handles only the image side: enrichment,
    image move, and EFU row creation.
    If `precomputed` is provided as (temp_row, label, confidence, label_source, predicted_name)
    from the preview phase, the enrichment API call is skipped entirely.
    """
    try:
        if not image_path.exists():
            print(f"  Image not found: {image_path}")
            return
        if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            print(f"  Not an image file: {image_path.name}")
            return

        print(f"Processing collection image: {image_path.name}")
        hints = parse_filename_hints(image_path.stem)

        if precomputed is not None:
            temp_row, label, confidence, label_source, _predicted_name = precomputed
        else:
            label, confidence, label_source = _classify_image_with_fallback(image_path, hints)
            # Pass raw sidecar text directly so enrich_vision_pass can combine it
            # with the image in a single API call instead of two separate calls.
            temp_row = _build_enriched_image_row(
                image_path=image_path,
                asset_type=asset_type,
                crc32_value=archive_crc32,
                archive_file_name=archive_file_name,
                hints=hints,
                session_context=session_context,
                session_hints=session_hints,
                author_input=author_input,
                vision_only=vision_only,
                text_hint_override=None,
                disable_web_search=disable_web_search,
                raw_sidecar_text=sidecar_text if sidecar_text else None,
                use_filename_signal=use_filename_signal,
            )
            # Collection mode policy: album tracks the source folder name.
            collection_album = image_path.parent.name.strip()
            if collection_album:
                temp_row["Album"] = collection_album

        # Collection mode: rename in the source folder, not in THUMBNAIL_BASE.
        # This keeps the files where they are but gives them the canonical name.
        image_dir = image_path.parent
        short_base = build_short_base_name(asset_type, temp_row, hints, fallback=image_path.stem)
        short_base_with_crc = f"{short_base}_{archive_crc32}"
        image_target = _make_unique_image_target(image_path, short_base_with_crc, image_dir)

        # If an old entry exists, delete the old (stale) file if it was already renamed,
        # then re-enrich with the fresh computed name and overwrite the EFU row.
        existing_entry = find_existing_index_entry_by_filename(METADATA_EFU_PATH, image_path.name)
        if existing_entry is not None:
            existing_img = (existing_entry.get("Filename") or "").strip()
            if existing_img and existing_img != "-":
                _ep_abs = Path(existing_img) if Path(existing_img).is_absolute() else image_dir / existing_img
                if _ep_abs.resolve() != image_path.resolve() and _ep_abs.exists():
                    _ep_abs.unlink()
                    print(f"  Deleted stale file: {_ep_abs.name}")
            print(f"  Re-ingesting: {image_path.name} (old entry replaced)")
        overwrite_existing = existing_entry is not None

        metadata_row = dict(temp_row)
        metadata_row["Filename"] = image_target.name
        metadata_row["ArchiveFile"] = archive_file_name
        metadata_row["CRC-32"] = archive_crc32

        print(f"(preview) Label: {label} | Source: {label_source} | Confidence: {confidence:.2%}")
        print(f"(preview) CRC-32: {archive_crc32}  (archive)")
        print(f"(preview) Image target: {image_target}")
        preview_mapped_metadata(asset_type, metadata_row)

        if dry_run:
            print("(dry-run) No files were moved and no metadata was written.")
            return

        if not auto_yes and not confirm_apply():
            print("Skipped by user.")
            return

        if image_path.resolve() != image_target.resolve():
            moved_image = _move_with_timeout(str(image_path), str(image_target))
        else:
            moved_image = image_target

        append_metadata_row(
            METADATA_EFU_PATH, metadata_row,
            overwrite_existing=overwrite_existing,
            overwrite_by_filename=str(image_path) if overwrite_existing else "",
        )
        print(f"Label: {label} | Source: {label_source} | Confidence: {confidence:.2%}")
        print(f"CRC-32: {archive_crc32}")
        print(f"Image renamed to: {moved_image}")
        if overwrite_existing:
            print(f"Metadata row overwritten in: {METADATA_EFU_PATH}")
        else:
            print(f"Metadata appended to: {METADATA_EFU_PATH}")

    except OSError as exc:
        import errno as _errno
        if exc.errno == _errno.EINVAL:
            print(f"Skipping — filename contains illegal characters: {image_path.name}")
        else:
            print(f"Error processing collection image {image_path}: {exc}")
    except Exception as exc:
        print(f"Error processing collection image {image_path}: {exc}")


def _prepare_collection_archive(
    archive_path: Path,
    dry_run: bool = False,
) -> tuple[str, str]:
    """Compute archive CRC-32, move it to ARCHIVE_BASE (once), return (crc32, final_name)."""
    # Dry-run should still preview the real archive CRC for accurate metadata/filename output.
    crc32 = compute_crc32(archive_path)

    # In no-move mode, keep archive filename/path as-is and only compute CRC.
    if not MOVE_FILES:
        if dry_run:
            print(f"(dry-run) Archive source kept: {archive_path}")
        else:
            print(f"Archive source kept: {archive_path}")
        return crc32, archive_path.name

    stem_clean = re.sub(r'[<>":?*|/\\]', "_", archive_path.stem)
    # Avoid repeated suffixes like "name_<CRC>_<CRC>.rar" on re-runs.
    stem_base = stem_clean
    if re.fullmatch(r"[0-9A-F]{8}", crc32):
        crc_token = crc32.upper()
        while re.search(rf"_{crc_token}$", stem_base, flags=re.IGNORECASE):
            stem_base = re.sub(rf"_{crc_token}$", "", stem_base, flags=re.IGNORECASE)
    final_name = f"{stem_base}_{crc32}{archive_path.suffix.lower()}"
    final_path = ARCHIVE_BASE / final_name

    if not dry_run:
        if final_path.exists() and final_path.resolve() == archive_path.resolve():
            pass  # already in place
        elif final_path.exists():
            print(f"Archive already at target: {final_path}")
        else:
            _move_with_timeout(str(archive_path), str(final_path))
            print(f"Archive moved to: {final_path}")
    else:
        print(f"(dry-run) Archive target would be: {final_path}")

    return crc32, final_name


def main() -> None:
    try:
        # Validate all base paths before any file operations.
        _validate_base_paths()
        # command-line flags
        dry_run = False
        auto_yes = False
        use_filename_signal = True
        asset_type: str | None = None
        ingest_mode: str = ""  # "pairs" | "collection" | "image-only" | "sidecar-collection"
        vision_only_enrichment = False
        sidecar_path: Path | None = None
        # Allow non-interactive invocation with multiple file arguments (pairs)
        def process_pair(
            image_path: Path,
            archive_path: Path,
            asset_type: str,
            dry_run: bool = False,
            auto_yes: bool = False,
            session_context: str = "",
            session_hints: dict[str, str] | None = None,
            use_filename_signal: bool = True,
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
                        confidence = 0.0
                        label_source = "stem"
                    # Feed vision label back as a hint so enrich_row_with_models
                    # can use it as a subject fallback (e.g. ModernSculpture → Sculpture).
                    hints["vision_label"] = label
                    hints["vision_confidence"] = f"{confidence:.6f}"
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
                if author_input:
                    temp_row["Author"] = author_input
                temp_row = enrich_row_with_models(
                    image_path=image_path,
                    source_stem=image_path.stem,
                    asset_type=asset_type,
                    hints=hints,
                    row=temp_row,
                    session_context=session_context,
                    session_hints=session_hints,
                    vision_only=vision_only_enrichment,
                    use_filename_signal=use_filename_signal,
                )
                # Restore user-provided Author — prevent AI enrichment from overwriting it.
                if author_input:
                    temp_row["Author"] = author_input
                # Pair mode should always rename both files:
                # - image always renames in place
                # - archive renames in place when MOVE_FILES=0, otherwise moves to ARCHIVE_BASE
                image_dir = image_path.parent
                archive_dir = ARCHIVE_BASE if MOVE_FILES else archive_path.parent
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
                        _existing_img_path = Path(existing_img)
                        image_target = _existing_img_path if _existing_img_path.is_absolute() else image_dir / existing_img
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

                # Always rename image in place.
                if overwrite_existing and image_target.exists() and image_target.resolve() != image_path.resolve():
                    image_target.unlink()
                if image_path.resolve() != image_target.resolve():
                    moved_image = _move_with_timeout(str(image_path), str(image_target))
                else:
                    moved_image = image_target

                # Always process archive target in pair mode:
                # in-place rename when MOVE_FILES=0, move+rename when MOVE_FILES=1.
                _, moved_archive = move_pair(
                    moved_image, archive_path, new_base_name,
                    image_target=moved_image,
                    archive_target=archive_target,
                    overwrite=overwrite_existing,
                    image_dir=image_dir,
                    archive_dir=archive_dir,
                )
                append_metadata_row(METADATA_EFU_PATH, metadata_row, overwrite_existing=overwrite_existing)
                print(f"Label: {label} | Source: {label_source} | Confidence: {confidence:.2%}")
                print(f"CRC-32: {crc32_value}")
                print(f"Image renamed to: {moved_image}")
                if moved_archive.resolve() != archive_path.resolve():
                    if MOVE_FILES:
                        print(f"Archive moved to: {moved_archive}")
                    else:
                        print(f"Archive renamed to: {moved_archive}")
                else:
                    print(f"Archive source kept: {moved_archive}")
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
            print("Usage:  python tools/ingest_asset.py [--asset-type=TYPE] [--dry-run|--quick] [--yes] IMAGE ARCHIVE [IMAGE ARCHIVE ...]")
            print()
            print("  IMAGE   — .jpg / .png render  |  ARCHIVE — matching archive or 3D model (same stem)")
            print("  TYPE    — furniture | fixture | vegetation | people | material | layouts | object | vehicle | vfx  (auto-detected if omitted)")
            print("  Options — --dry-run / --quick  |  --yes / -y  |  --nofilename")
            print()
            print("  Run with -h for full reference and examples.")
            print()
        clean_args: list[str] = []
        quick_alias_used = False
        unknown_options: list[str] = []
        expect_sidecar_path = False
        for a in argv:
            if expect_sidecar_path:
                if a.startswith("-"):
                    raise ValueError("--sidecar requires a file path value.")
                sidecar_path = Path(a.strip().strip('"').strip("'"))
                expect_sidecar_path = False
                continue
            if a in {"--dry-run", "--quick"}:
                dry_run = True
                if a == "--quick":
                    quick_alias_used = True
            elif a in {"--yes", "-y"}:
                auto_yes = True
            elif a == "--nofilename":
                use_filename_signal = False
            elif a.startswith("--asset-type="):
                asset_type = normalize_asset_type(a.split("=", 1)[1])
            elif a.startswith("--ingest-mode="):
                ingest_mode = a.split("=", 1)[1].strip().lower()
            elif a.startswith("--sidecar="):
                sidecar_path = Path(a.split("=", 1)[1].strip().strip('"'))
            elif a == "--sidecar":
                expect_sidecar_path = True
            elif a.startswith("--backend=") or a in {
                "--online", "--local", "--vision-detect", "--vision-only",
                "--enrich-source=hybrid", "--enrich-source=vision-only",
                "--enrich-mode=vision", "--enrich-mode=both", "--enrich-mode=text",
            }:
                # Legacy flags are accepted for compatibility and ignored.
                continue
            elif a.startswith("--enrich-source="):
                # Legacy enrich-source flag is accepted and ignored.
                continue
            elif a.startswith("-"):
                unknown_options.append(a)
            else:
                clean_args.append(a)

        if expect_sidecar_path:
            raise ValueError("--sidecar requires a file path value.")

        if unknown_options:
            raise ValueError(
                "Unknown option(s): " + ", ".join(unknown_options) + ". Run with -h for supported flags."
            )
        _valid_modes = {"pairs", "collection", "image-only", "sidecar-collection"}
        if ingest_mode and ingest_mode not in _valid_modes:
            raise ValueError(
                f"Unknown --ingest-mode: '{ingest_mode}'. Valid values: " + ", ".join(sorted(_valid_modes))
            )
        if quick_alias_used and sys.stdout.isatty():
            print("Note: --quick is treated as a legacy alias for --dry-run.")
        if not use_filename_signal and sys.stdout.isatty():
            print("Filename signal disabled for AI inference (--nofilename).")
        # Unified enrichment flow always runs vision extraction when images are present.
        vision_detect = True

        if asset_type and asset_type not in ASSET_TYPES:
            raise ValueError(f"Unsupported asset type: {asset_type}")

        if not asset_type:
            if sys.stdout.isatty():
                asset_type = prompt_asset_type_choice()
                print(f"Asset type: {asset_type}")
            else:
                raise ValueError("Missing --asset-type in non-interactive mode.")

        # Interactive session context prompt removed to reduce friction.
        # Default to no session context; parse_session_context handles empty.
        session_context = ""
        session_hints: dict[str, str] = {}

        # ── Mode selection ─────────────────────────────────────────────────
        # Auto-detect when file paths are provided on the command line.
        # For interactive paste mode (no clean_args), detection is deferred
        # until after pasted paths are collected.
        if not ingest_mode:
            if clean_args:
                ingest_mode = detect_ingest_mode_from_paths([Path(p) for p in clean_args], sidecar_path=sidecar_path)
                if sys.stdout.isatty():
                    print(f"Ingest mode auto-detected: {ingest_mode}")
            elif not sys.stdout.isatty():
                ingest_mode = "pairs"
        if sys.stdout.isatty():
            if ingest_mode:
                print(f"Ingest mode: {ingest_mode}")
                print()
        # Fixed policy: always run AI-first hybrid enrichment; no source selection.
        vision_only_enrichment = False

        author_input = "-"

        if len(clean_args) >= 2:
            # Treat all args as a flat list of files.
            arg_paths = [Path(p) for p in clean_args]

            # Runtime metadata target: .metadata.efu in the input folder.
            _runtime_metadata_path = resolve_metadata_efu_path_from_inputs(arg_paths)
            set_runtime_metadata_efu_path(_runtime_metadata_path)
            if sys.stdout.isatty():
                print(f"Metadata target: {METADATA_EFU_PATH}")

            # Auto-detect sidecar file from the pasted/CLI file list.
            if ingest_mode == "sidecar-collection" and sidecar_path is None:
                _sidecar_exts = {".csv", ".txt", ".md"}
                _csv_args = [p for p in arg_paths if p.suffix.lower() in _sidecar_exts]
                if len(_csv_args) == 1:
                    sidecar_path = _csv_args[0]
                    arg_paths = [p for p in arg_paths if p != sidecar_path]
                    print(f"Sidecar auto-detected from args: {sidecar_path.name}")

            author_input = derive_author_from_sources(arg_paths, sidecar_path)
            if sys.stdout.isatty():
                print(f"Author auto-set from parent folder: {author_input}")

            if ingest_mode == "image-only":
                # ─ image-only: each image gets its own CRC-32 from itself
                images = [p for p in arg_paths if p.suffix.lower() in IMAGE_EXTENSIONS]
                if not images:
                    print("No image files found in arguments.")
                else:
                    if sys.stdout.isatty():
                        print(f"Processing {len(images)} image(s) (image-only mode)...")
                    batch_confirm = len(images) > 1 and not dry_run and not auto_yes
                    if batch_confirm:
                        print("Batch preview (no writes yet):")
                        pre_processed = 0
                        for img_path in images:
                            if img_path.exists():
                                process_image_only(
                                    img_path,
                                    asset_type=asset_type,
                                    dry_run=True,
                                    auto_yes=True,
                                    session_context=session_context,
                                    session_hints=session_hints,
                                    author_input=author_input,
                                    vision_only=vision_only_enrichment,
                                    use_filename_signal=use_filename_signal,
                                )
                            else:
                                print(f"  Image not found: {img_path}")
                            pre_processed += 1
                            if sys.stdout.isatty():
                                _print_progress(pre_processed, len(images))
                        if not confirm_apply_all(len(images), "image(s)"):
                            print("Skipped by user.")
                            return

                    run_dry = False if batch_confirm else dry_run
                    run_yes = True if batch_confirm else auto_yes
                    processed = 0
                    for img_path in images:
                        if img_path.exists():
                            process_image_only(
                                img_path,
                                asset_type=asset_type,
                                dry_run=run_dry,
                                auto_yes=run_yes,
                                session_context=session_context,
                                session_hints=session_hints,
                                author_input=author_input,
                                vision_only=vision_only_enrichment,
                                use_filename_signal=use_filename_signal,
                            )
                        else:
                            print(f"  Image not found: {img_path}")
                        processed += 1
                        if sys.stdout.isatty():
                            _print_progress(processed, len(images))

            elif ingest_mode == "collection":
                # ─ collection: many images share one archive's CRC-32
                images = [p for p in arg_paths if p.suffix.lower() in IMAGE_EXTENSIONS and p.exists()]
                archives = [p for p in arg_paths if p.suffix.lower() in ASSET_FILE_EXTENSIONS and p.exists()]
                if len(archives) != 1:
                    print(f"[ERROR] collection mode requires exactly 1 archive; found {len(archives)}.")
                    print("  Archives detected:", [str(a) for a in archives] or "(none)")
                elif not images:
                    print("[ERROR] collection mode: no image files found in arguments.")
                else:
                    _col_archive = archives[0]
                    if sys.stdout.isatty():
                        print(f"Collection: {len(images)} image(s) → archive: {_col_archive.name}")

                    batch_confirm = len(images) > 1 and not dry_run and not auto_yes
                    if batch_confirm:
                        print("Batch preview (no writes yet):")
                        _pre_crc32, _pre_arc_name = _prepare_collection_archive(_col_archive, dry_run=True)
                        pre_processed = 0
                        for img_path in images:
                            process_collection_image(
                                img_path,
                                archive_crc32=_pre_crc32,
                                archive_file_name=_pre_arc_name,
                                asset_type=asset_type,
                                dry_run=True,
                                auto_yes=True,
                                session_context=session_context,
                                session_hints=session_hints,
                                author_input=author_input,
                                vision_only=vision_only_enrichment,
                                use_filename_signal=use_filename_signal,
                            )
                            pre_processed += 1
                            if sys.stdout.isatty():
                                _print_progress(pre_processed, len(images))
                        if not confirm_apply_all(len(images), "image(s)"):
                            print("Skipped by user.")
                            return
                        _col_crc32, _col_arc_name = _prepare_collection_archive(_col_archive, dry_run=False)
                        run_dry = False
                        run_yes = True
                    else:
                        _col_crc32, _col_arc_name = _prepare_collection_archive(_col_archive, dry_run=dry_run)
                        run_dry = dry_run
                        run_yes = auto_yes

                    processed = 0
                    for img_path in images:
                        process_collection_image(
                            img_path,
                            archive_crc32=_col_crc32,
                            archive_file_name=_col_arc_name,
                            asset_type=asset_type, dry_run=run_dry, auto_yes=run_yes,
                            session_context=session_context, session_hints=session_hints,
                            author_input=author_input,
                            vision_only=vision_only_enrichment,
                            use_filename_signal=use_filename_signal,
                        )
                        processed += 1
                        if sys.stdout.isatty():
                            _print_progress(processed, len(images))

            elif ingest_mode == "sidecar-collection":
                # ─ sidecar-collection: many images share one archive + sidecar text map
                if sidecar_path is None:
                    raise ValueError(
                        "sidecar-collection mode requires a sidecar file (.csv/.md/.txt) — "
                        "paste it together with the images and archive, or use --sidecar=PATH"
                    )
                if not sidecar_path.exists() or sidecar_path.suffix.lower() not in {".txt", ".md", ".csv"}:
                    raise ValueError(f"Invalid sidecar file: {sidecar_path}")

                images = [p for p in arg_paths if p.suffix.lower() in IMAGE_EXTENSIONS and p.exists()]
                archives = [p for p in arg_paths if p.suffix.lower() in ASSET_FILE_EXTENSIONS and p.exists()]
                if len(archives) == 0:
                    auto_archives = _autodetect_archive_from_sidecar_folder(sidecar_path)
                    if len(auto_archives) == 1:
                        archives = [auto_archives[0]]
                        print(f"Auto-detected archive from sidecar folder: {auto_archives[0]}")
                if len(archives) != 1:
                    print(f"[ERROR] sidecar-collection mode requires exactly 1 archive; found {len(archives)}.")
                    print("  Archives detected:", [str(a) for a in archives] or "(none)")
                elif not images:
                    print("[ERROR] sidecar-collection mode: no image files found in arguments.")
                else:
                    sidecar_entries = parse_sidecar_entries(sidecar_path)
                    if not sidecar_entries:
                        print(f"[WARN] No parsable sidecar entries found in: {sidecar_path}")
                    else:
                        print(f"Sidecar loaded: {sidecar_path} ({len(sidecar_entries)} entries)")

                    _col_archive = archives[0]
                    if sys.stdout.isatty():
                        print(f"Sidecar collection: {len(images)} image(s) → archive: {_col_archive.name}")
                    _col_crc32, _col_arc_name = _prepare_collection_archive(_col_archive, dry_run=dry_run)
                    _preview_cache = _show_sidecar_collection_preview(
                        images, sidecar_entries, _col_crc32,
                        archive_file_name=_col_arc_name,
                        asset_type=asset_type,
                        session_context=session_context,
                        session_hints=session_hints,
                        author_input=author_input,
                        vision_only=vision_only_enrichment,
                        dry_run=dry_run,
                        auto_yes=auto_yes,
                    )
                    if _preview_cache is None:
                        return
                    processed = 0
                    sidecar_hits = 0
                    for img_path in images:
                        page_key = extract_page_key_from_stem(img_path.stem)
                        _st, matched_key = resolve_sidecar_text_for_image(sidecar_entries, img_path, page_key)
                        if _st:
                            sidecar_hits += 1
                        process_collection_image(
                            img_path,
                            archive_crc32=_col_crc32,
                            archive_file_name=_col_arc_name,
                            asset_type=asset_type,
                            dry_run=dry_run,
                            auto_yes=True,
                            session_context=session_context,
                            session_hints=session_hints,
                            author_input=author_input,
                            vision_only=vision_only_enrichment,
                            sidecar_text=_st,
                            disable_web_search=True,
                            precomputed=_preview_cache.get(str(img_path)),
                            use_filename_signal=use_filename_signal,
                        )
                        processed += 1
                        if sys.stdout.isatty():
                            _print_progress(processed, len(images))
                    print(f"Sidecar mapping summary: {sidecar_hits}/{len(images)} images matched")

            else:
                # ─ pairs (default): stem-based matching; re-enrich if all images
                # Check if all args are image files (re-enrich mode) vs looking for pairs.
                # Use provided path suffixes directly so mode behavior is deterministic
                # even when a file is missing.
                _arg_kinds = [_pair_kind(p) for p in arg_paths]
                all_images = bool(_arg_kinds) and all(k == "image" for k in _arg_kinds)
                has_archives = any(k == "asset" for k in _arg_kinds)

                if all_images and not has_archives:
                    # Re-enrich mode: all args are images, no archives provided
                    if sys.stdout.isatty():
                        print(f"Re-enrich mode detected: {len(arg_paths)} image(s) without archives")
                        print("Images will be re-enriched using existing metadata as base.")
                        print()
                    batch_confirm = len(arg_paths) > 1 and not dry_run and not auto_yes
                    if batch_confirm:
                        print("Batch preview (no writes yet):")
                        pre_processed = 0
                        for img_path in arg_paths:
                            if img_path.exists():
                                process_reenrich(
                                    img_path,
                                    asset_type=asset_type,
                                    dry_run=True,
                                    auto_yes=True,
                                    session_context=session_context,
                                    session_hints=session_hints,
                                    vision_only=vision_only_enrichment,
                                    use_filename_signal=use_filename_signal,
                                )
                            else:
                                print(f"  Image not found: {img_path}")
                            pre_processed += 1
                            if sys.stdout.isatty():
                                _print_progress(pre_processed, len(arg_paths))
                        if not confirm_apply_all(len(arg_paths), "image(s)"):
                            print("Skipped by user.")
                            return

                    run_dry = False if batch_confirm else dry_run
                    run_yes = True if batch_confirm else auto_yes
                    processed = 0
                    for img_path in arg_paths:
                        if img_path.exists():
                            process_reenrich(
                                img_path,
                                asset_type=asset_type,
                                dry_run=run_dry,
                                auto_yes=run_yes,
                                session_context=session_context,
                                session_hints=session_hints,
                                vision_only=vision_only_enrichment,
                                use_filename_signal=use_filename_signal,
                            )
                        else:
                            print(f"  Image not found: {img_path}")
                        processed += 1
                        if sys.stdout.isatty():
                            _print_progress(processed, len(arg_paths))
                else:
                    # Standard pairing mode: looking for image/archive pairs
                    from collections import defaultdict

                    stems: dict[str, list[Path]] = defaultdict(list)
                    for p in arg_paths:
                        stems[p.stem].append(p)

                    stems_items = list(stems.items())
                    total = len(stems_items)
                    if total == 0:
                        print("No file pairs found in arguments.")
                    else:
                        valid_pairs = 0
                        for stem, items in stems_items:
                            if len(items) != 2:
                                continue
                            a, b = items
                            if (a.suffix.lower() in IMAGE_EXTENSIONS and b.suffix.lower() in ASSET_FILE_EXTENSIONS) or \
                               (b.suffix.lower() in IMAGE_EXTENSIONS and a.suffix.lower() in ASSET_FILE_EXTENSIONS):
                                valid_pairs += 1

                        batch_confirm = valid_pairs > 1 and not dry_run and not auto_yes
                        if batch_confirm:
                            print("Batch preview (no writes yet):")
                            pre_processed = 0
                            for stem, items in stems_items:
                                if len(items) != 2:
                                    _print_unpaired_group(stem, items, arg_paths)
                                    pre_processed += 1
                                    _print_progress(pre_processed, total)
                                    continue
                                a, b = items
                                if a.suffix.lower() in IMAGE_EXTENSIONS and b.suffix.lower() in ASSET_FILE_EXTENSIONS:
                                    process_pair(a, b, asset_type=asset_type, dry_run=True, auto_yes=True, session_context=session_context, session_hints=session_hints, use_filename_signal=use_filename_signal)
                                elif b.suffix.lower() in IMAGE_EXTENSIONS and a.suffix.lower() in ASSET_FILE_EXTENSIONS:
                                    process_pair(b, a, asset_type=asset_type, dry_run=True, auto_yes=True, session_context=session_context, session_hints=session_hints, use_filename_signal=use_filename_signal)
                                else:
                                    print(f"Skipping stem '{stem}': could not identify image/asset pair ({a}, {b})")
                                pre_processed += 1
                                _print_progress(pre_processed, total)
                            if not confirm_apply_all(valid_pairs, "pair(s)"):
                                print("Skipped by user.")
                                return

                        run_dry = False if batch_confirm else dry_run
                        run_yes = True if batch_confirm else auto_yes
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
                                process_pair(a, b, asset_type=asset_type, dry_run=run_dry, auto_yes=run_yes, session_context=session_context, session_hints=session_hints, use_filename_signal=use_filename_signal)
                            elif b.suffix.lower() in IMAGE_EXTENSIONS and a.suffix.lower() in ASSET_FILE_EXTENSIONS:
                                process_pair(b, a, asset_type=asset_type, dry_run=run_dry, auto_yes=run_yes, session_context=session_context, session_hints=session_hints, use_filename_signal=use_filename_signal)
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

            # Runtime metadata target: .metadata.efu in the pasted input folder.
            _runtime_metadata_path = resolve_metadata_efu_path_from_inputs(valid_paste_paths)
            set_runtime_metadata_efu_path(_runtime_metadata_path)
            if sys.stdout.isatty():
                print(f"Metadata target: {METADATA_EFU_PATH}")

            # Auto-detect mode for pasted paths when not explicitly set.
            if not ingest_mode:
                ingest_mode = detect_ingest_mode_from_paths(valid_paste_paths, sidecar_path=sidecar_path)
                if sys.stdout.isatty():
                    print(f"Ingest mode auto-detected: {ingest_mode}")
                    print()

            author_input = derive_author_from_sources(valid_paste_paths, sidecar_path)
            if sys.stdout.isatty():
                print(f"Author auto-set from parent folder: {author_input}")

            # Detect asset type from pasted paths when not supplied via --asset-type=.
            if not asset_type:
                if sys.stdout.isatty():
                    asset_type = prompt_asset_type_choice()
                    print(f"Asset type: {asset_type}")
                else:
                    raise ValueError("Missing --asset-type in non-interactive mode.")

            print(f"Processing {total} item(s)...")

            if ingest_mode == "image-only":
                # ─ image-only
                paste_images = [p for p in valid_paste_paths if p.suffix.lower() in IMAGE_EXTENSIONS]
                if not paste_images:
                    print("No image files found in pasted paths.")
                else:
                    batch_confirm = len(paste_images) > 1 and not dry_run and not auto_yes
                    if batch_confirm:
                        print("Batch preview (no writes yet):")
                        pre_processed = 0
                        for img_path in paste_images:
                            process_image_only(
                                img_path,
                                asset_type=asset_type,
                                dry_run=True,
                                auto_yes=True,
                                session_context=session_context,
                                session_hints=session_hints,
                                author_input=author_input,
                                vision_only=vision_only_enrichment,
                                use_filename_signal=use_filename_signal,
                            )
                            pre_processed += 1
                            if sys.stdout.isatty():
                                _print_progress(pre_processed, len(paste_images))
                        if not confirm_apply_all(len(paste_images), "image(s)"):
                            print("Skipped by user.")
                            return

                    run_dry = False if batch_confirm else dry_run
                    run_yes = True if batch_confirm else auto_yes
                    processed = 0
                    for img_path in paste_images:
                        process_image_only(
                            img_path,
                            asset_type=asset_type,
                            dry_run=run_dry,
                            auto_yes=run_yes,
                            session_context=session_context,
                            session_hints=session_hints,
                            author_input=author_input,
                            vision_only=vision_only_enrichment,
                            use_filename_signal=use_filename_signal,
                        )
                        processed += 1
                        if sys.stdout.isatty():
                            _print_progress(processed, len(paste_images))

            elif ingest_mode == "collection":
                # ─ collection: many images share one archive's CRC-32
                paste_images = [p for p in valid_paste_paths if p.suffix.lower() in IMAGE_EXTENSIONS]
                paste_archives = [p for p in valid_paste_paths if p.suffix.lower() in ASSET_FILE_EXTENSIONS]
                if len(paste_archives) != 1:
                    print(f"[ERROR] collection mode requires exactly 1 archive; found {len(paste_archives)}.")
                    print("  Archives detected:", [str(a) for a in paste_archives] or "(none)")
                elif not paste_images:
                    print("[ERROR] collection mode: no image files found in pasted paths.")
                else:
                    _col_archive = paste_archives[0]
                    if sys.stdout.isatty():
                        print(f"Collection: {len(paste_images)} image(s) → archive: {_col_archive.name}")

                    batch_confirm = len(paste_images) > 1 and not dry_run and not auto_yes
                    if batch_confirm:
                        print("Batch preview (no writes yet):")
                        _pre_crc32, _pre_arc_name = _prepare_collection_archive(_col_archive, dry_run=True)
                        pre_processed = 0
                        for img_path in paste_images:
                            process_collection_image(
                                img_path,
                                archive_crc32=_pre_crc32,
                                archive_file_name=_pre_arc_name,
                                asset_type=asset_type,
                                dry_run=True,
                                auto_yes=True,
                                session_context=session_context,
                                session_hints=session_hints,
                                author_input=author_input,
                                vision_only=vision_only_enrichment,
                                use_filename_signal=use_filename_signal,
                            )
                            pre_processed += 1
                            if sys.stdout.isatty():
                                _print_progress(pre_processed, len(paste_images))
                        if not confirm_apply_all(len(paste_images), "image(s)"):
                            print("Skipped by user.")
                            return
                        _col_crc32, _col_arc_name = _prepare_collection_archive(_col_archive, dry_run=False)
                        run_dry = False
                        run_yes = True
                    else:
                        _col_crc32, _col_arc_name = _prepare_collection_archive(_col_archive, dry_run=dry_run)
                        run_dry = dry_run
                        run_yes = auto_yes

                    processed = 0
                    for img_path in paste_images:
                        process_collection_image(
                            img_path,
                            archive_crc32=_col_crc32,
                            archive_file_name=_col_arc_name,
                            asset_type=asset_type, dry_run=run_dry, auto_yes=run_yes,
                            session_context=session_context, session_hints=session_hints,
                            author_input=author_input,
                            vision_only=vision_only_enrichment,
                            use_filename_signal=use_filename_signal,
                        )
                        processed += 1
                        if sys.stdout.isatty():
                            _print_progress(processed, len(paste_images))

            elif ingest_mode == "sidecar-collection":
                # ─ sidecar-collection: many images share one archive + sidecar text map
                # Auto-detect sidecar file from the pasted file list.
                if sidecar_path is None:
                    _sidecar_exts = {".csv", ".txt", ".md"}
                    _csv_paste = [p for p in valid_paste_paths if p.suffix.lower() in _sidecar_exts]
                    if len(_csv_paste) == 1:
                        sidecar_path = _csv_paste[0]
                        print(f"Sidecar auto-detected from pasted paths: {sidecar_path.name}")
                if sidecar_path is None:
                    raise ValueError(
                        "sidecar-collection mode requires a sidecar file (.csv/.md/.txt) — "
                        "paste it together with the images and archive, or use --sidecar=PATH"
                    )
                if not sidecar_path.exists() or sidecar_path.suffix.lower() not in {".txt", ".md", ".csv"}:
                    raise ValueError(f"Invalid sidecar file: {sidecar_path}")

                paste_images = [p for p in valid_paste_paths if p.suffix.lower() in IMAGE_EXTENSIONS]
                paste_archives = [p for p in valid_paste_paths if p.suffix.lower() in ASSET_FILE_EXTENSIONS]
                if len(paste_archives) == 0:
                    auto_archives = _autodetect_archive_from_sidecar_folder(sidecar_path)
                    if len(auto_archives) == 1:
                        paste_archives = [auto_archives[0]]
                        print(f"Auto-detected archive from sidecar folder: {auto_archives[0]}")
                if len(paste_archives) != 1:
                    print(f"[ERROR] sidecar-collection mode requires exactly 1 archive; found {len(paste_archives)}.")
                    print("  Archives detected:", [str(a) for a in paste_archives] or "(none)")
                elif not paste_images:
                    print("[ERROR] sidecar-collection mode: no image files found in pasted paths.")
                else:
                    sidecar_entries = parse_sidecar_entries(sidecar_path)
                    if not sidecar_entries:
                        print(f"[WARN] No parsable sidecar entries found in: {sidecar_path}")
                    else:
                        print(f"Sidecar loaded: {sidecar_path} ({len(sidecar_entries)} entries)")

                    _col_archive = paste_archives[0]
                    if sys.stdout.isatty():
                        print(f"Sidecar collection: {len(paste_images)} image(s) → archive: {_col_archive.name}")
                    _col_crc32, _col_arc_name = _prepare_collection_archive(_col_archive, dry_run=dry_run)
                    _preview_cache = _show_sidecar_collection_preview(
                        paste_images, sidecar_entries, _col_crc32,
                        archive_file_name=_col_arc_name,
                        asset_type=asset_type,
                        session_context=session_context,
                        session_hints=session_hints,
                        author_input=author_input,
                        vision_only=vision_only_enrichment,
                        dry_run=dry_run,
                        auto_yes=auto_yes,
                    )
                    if _preview_cache is None:
                        return
                    processed = 0
                    sidecar_hits = 0
                    for img_path in paste_images:
                        page_key = extract_page_key_from_stem(img_path.stem)
                        _st, matched_key = resolve_sidecar_text_for_image(sidecar_entries, img_path, page_key)
                        if _st:
                            sidecar_hits += 1
                        process_collection_image(
                            img_path,
                            archive_crc32=_col_crc32,
                            archive_file_name=_col_arc_name,
                            asset_type=asset_type,
                            dry_run=dry_run,
                            auto_yes=True,
                            session_context=session_context,
                            session_hints=session_hints,
                            author_input=author_input,
                            vision_only=vision_only_enrichment,
                            sidecar_text=_st,
                            disable_web_search=True,
                            precomputed=_preview_cache.get(str(img_path)),
                            use_filename_signal=use_filename_signal,
                        )
                        processed += 1
                        if sys.stdout.isatty():
                            _print_progress(processed, len(paste_images))
                    print(f"Sidecar mapping summary: {sidecar_hits}/{len(paste_images)} images matched")

            else:
                # ─ pairs (default): re-enrich if all images, else stem-based pairing
                # Check if all items are image files (re-enrich mode)
                _paste_kinds = [_pair_kind(p) for p in valid_paste_paths]
                all_paste_images = bool(_paste_kinds) and all(k == "image" for k in _paste_kinds)
                paste_has_archives = any(k == "asset" for k in _paste_kinds)

                if all_paste_images and not paste_has_archives:
                    # Re-enrich mode in paste: all items are images, no archives
                    if sys.stdout.isatty():
                        print("Re-enrich mode detected: all items are images without archives")
                        print("Images will be re-enriched using existing metadata as base.")
                        print()
                    batch_confirm = len(valid_paste_paths) > 1 and not dry_run and not auto_yes
                    if batch_confirm:
                        print("Batch preview (no writes yet):")
                        pre_processed = 0
                        for img_path in valid_paste_paths:
                            process_reenrich(
                                img_path,
                                asset_type=asset_type,
                                dry_run=True,
                                auto_yes=True,
                                session_context=session_context,
                                session_hints=session_hints,
                                vision_only=vision_only_enrichment,
                                use_filename_signal=use_filename_signal,
                            )
                            pre_processed += 1
                            if sys.stdout.isatty():
                                _print_progress(pre_processed, len(valid_paste_paths))
                        if not confirm_apply_all(len(valid_paste_paths), "image(s)"):
                            print("Skipped by user.")
                            return

                    run_dry = False if batch_confirm else dry_run
                    run_yes = True if batch_confirm else auto_yes
                    processed = 0
                    for img_path in valid_paste_paths:
                        process_reenrich(
                            img_path,
                            asset_type=asset_type,
                            dry_run=run_dry,
                            auto_yes=run_yes,
                            session_context=session_context,
                            session_hints=session_hints,
                            vision_only=vision_only_enrichment,
                            use_filename_signal=use_filename_signal,
                        )
                        processed += 1
                        if sys.stdout.isatty():
                            _print_progress(processed, len(valid_paste_paths))
                else:
                    # Standard pairing mode: looking for image/archive pairs
                    valid_pairs = 0
                    for stem, items in paste_items:
                        if len(items) != 2:
                            continue
                        a, b = items
                        if (a.suffix.lower() in IMAGE_EXTENSIONS and b.suffix.lower() in ASSET_FILE_EXTENSIONS) or \
                           (b.suffix.lower() in IMAGE_EXTENSIONS and a.suffix.lower() in ASSET_FILE_EXTENSIONS):
                            valid_pairs += 1

                    batch_confirm = valid_pairs > 1 and not dry_run and not auto_yes
                    if batch_confirm:
                        print("Batch preview (no writes yet):")
                        pre_processed = 0
                        for stem, items in paste_items:
                            if len(items) != 2:
                                _print_unpaired_group(stem, items, valid_paste_paths, indent="  ")
                                pre_processed += 1
                                _print_progress(pre_processed, total)
                                continue
                            a, b = items
                            if a.suffix.lower() in IMAGE_EXTENSIONS and b.suffix.lower() in ASSET_FILE_EXTENSIONS:
                                process_pair(a, b, asset_type=asset_type, dry_run=True, auto_yes=True, session_context=session_context, session_hints=session_hints, use_filename_signal=use_filename_signal)
                            elif b.suffix.lower() in IMAGE_EXTENSIONS and a.suffix.lower() in ASSET_FILE_EXTENSIONS:
                                process_pair(b, a, asset_type=asset_type, dry_run=True, auto_yes=True, session_context=session_context, session_hints=session_hints, use_filename_signal=use_filename_signal)
                            else:
                                print(f"  Skipping '{stem}': could not identify image/asset pair")
                            pre_processed += 1
                            _print_progress(pre_processed, total)
                        if not confirm_apply_all(valid_pairs, "pair(s)"):
                            print("Skipped by user.")
                            return

                    run_dry = False if batch_confirm else dry_run
                    run_yes = True if batch_confirm else auto_yes
                    processed = 0
                    for stem, items in paste_items:
                        if len(items) != 2:
                            _print_unpaired_group(stem, items, valid_paste_paths, indent="  ")
                            processed += 1
                            _print_progress(processed, total)
                            continue
                        a, b = items
                        if a.suffix.lower() in IMAGE_EXTENSIONS and b.suffix.lower() in ASSET_FILE_EXTENSIONS:
                            process_pair(a, b, asset_type=asset_type, dry_run=run_dry, auto_yes=run_yes, session_context=session_context, session_hints=session_hints, use_filename_signal=use_filename_signal)
                        elif b.suffix.lower() in IMAGE_EXTENSIONS and a.suffix.lower() in ASSET_FILE_EXTENSIONS:
                            process_pair(b, a, asset_type=asset_type, dry_run=run_dry, auto_yes=run_yes, session_context=session_context, session_hints=session_hints, use_filename_signal=use_filename_signal)
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


