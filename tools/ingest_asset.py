from __future__ import annotations

import re
import shutil
import sys
import zlib
import csv
from functools import lru_cache
from pathlib import Path

import open_clip
import torch
from PIL import Image
import base64
import json
import urllib.request
import subprocess
import threading
import itertools
import time
import textwrap

THUMBNAIL_BASE = Path(r"D:\DB")
ARCHIVE_BASE = Path(r"G:\DB")
# Use a hidden index file to avoid collisions with user files.
METADATA_EFU_PATH = THUMBNAIL_BASE / ".metadata.efu"
# Legacy alias kept for any code that still references OUTPUT_DIR directly.
OUTPUT_DIR = THUMBNAIL_BASE
# Previous DB export used as a supplementary enrichment source.
# Keys are lowercase bare filename stems (no extension, no vendor folder prefix).
CURRENT_DB_PATH = Path(r"E:\Database\CurrentDB.csv")
_CURRENT_DB_CACHE: dict[str, dict[str, str]] | None = None


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
def _kw_keyword_map() -> list[tuple[str, str]]:
    """Return [(keyword_lower, subcategory), …] from the Keyword Map section.

    Order is preserved from the file (multi-word entries should appear first).
    """
    rows = _load_ingest_keywords().get("Keyword Map", [])
    return [(r[0].lower(), r[1]) for r in rows if len(r) >= 2 and r[0] and r[1]]


@lru_cache(maxsize=1)
def _kw_subcategories() -> set[str]:
    """Return the full set of allowed subcategory names."""
    rows = _load_ingest_keywords().get("Subcategory Allowlist", [])
    return {r[0] for r in rows if r and r[0]}


@lru_cache(maxsize=1)
def _kw_subcategory_groups() -> dict[str, str]:
    """Return {subcategory: group_path} from the Subcategory Allowlist section."""
    rows = _load_ingest_keywords().get("Subcategory Allowlist", [])
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


@lru_cache(maxsize=1)
def _kw_clip_labels() -> list[str]:
    """Return CLIP label candidates in file order."""
    rows = _load_ingest_keywords().get("CLIP Labels", [])
    return [r[0] for r in rows if r and r[0]]


# ---------------------------------------------------------------------------

MODEL_NAME = "ViT-L-14"
PRETRAINED = "openai"
CUSTOM_LABEL_MIN_CONFIDENCE = 0.30
OLLAMA_VISION_MODEL = "qwen3-vl:latest"   # vision pass: image + filename → raw metadata
# Text pass removed — we no longer use a text-normalizer model.
OLLAMA_TEXT_MODEL: str | None = None
OLLAMA_MODEL = OLLAMA_VISION_MODEL           # legacy alias used by classify_image / clean_name_with_qwen
OLLAMA_ENDPOINT = "http://127.0.0.1:11434/api/generate"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
ARCHIVE_EXTENSIONS = {".zip", ".rar", ".7z"}

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
    "Rating",
    "Tags",
    "URL",
    "From",
    "Mood",
    "Author",
    "Writer",
    "Album",
    "Genre",
    "People",
    "Company",
    "Period",
    "Artist",
    "Title",
    "Comment",
    "To",
    "Manager",
    "Subject",
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
        # Show a simple loading bar with a percentage instead of a spinner.
        width = 30
        progress = 0.0
        step = 3.0
        label = self._msg.ljust(self._LABEL_WIDTH)
        try:
            while not self._stop.is_set():
                filled = int(width * progress / 100)
                bar = "[" + "#" * filled + "-" * (width - filled) + "]"
                try:
                    sys.stderr.write(f"\r{label} {bar} {progress:5.1f}%")
                    sys.stderr.flush()
                except Exception:
                    pass
                time.sleep(0.12)
                progress += step
                if progress >= 95.0:
                    # stay near-complete while waiting for the real stop event
                    progress = 90.0
            # on stop, show complete state
            try:
                sys.stderr.write(f"\r{label} [" + "#" * width + "] 100.0%" + " " * 10 + "\n")
                sys.stderr.flush()
            except Exception:
                pass
        except Exception:
            # Fallback to a minimal indicator on failure
            try:
                sys.stderr.write(f"\r{label}\n")
                sys.stderr.flush()
            except Exception:
                pass

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join()


def _print_help_table() -> None:
    table = [
        ("Flag", "Meaning"),
        ("--dry-run", "Preview only; do not move files or write index"),
        ("--quick", "Skip vision model; derive labels from filename"),
        ("--yes, -y", "Auto-confirm apply (no prompt)") ,
        ("--asset-type=TYPE", "Set asset type (furniture|vegetation|people|material|buildings|layouts)"),
        ("-h, --help", "Show this help and exit"),
    ]
    col1_w = max(len(r[0]) for r in table) + 2
    col2_w = max(len(r[1]) for r in table) + 2
    sep = "+" + "-" * col1_w + "+" + "-" * col2_w + "+"
    print(sep)
    print(f"| {table[0][0].ljust(col1_w-2)} | {table[0][1].ljust(col2_w-2)} |")
    print(sep)
    for k, v in table[1:]:
        print(f"| {k.ljust(col1_w-2)} | {v.ljust(col2_w-2)} |")
    print(sep)
    print()
    examples = textwrap.dedent(
        """
        Examples:
          python tools/ingest_asset.py --dry-run --quick --asset-type=furniture <image> <archive>
          python tools/ingest_asset.py --yes --asset-type=furniture <image> <archive>
        """
    ).strip()
    print(examples)
    print()


def _print_progress(current: int, total: int, width: int = 30) -> None:
    if total <= 0:
        return
    filled = int(width * current / total)
    bar = "[" + "#" * filled + "-" * (width - filled) + "]"
    pct = (current / total) * 100
    print(f"Progress: {current}/{total} {bar} {pct:5.1f}%")


def show_startup_loading(duration: float = 1.2, width: int = 30) -> None:
    """Show a short startup loading bar for a tidier CLI experience."""
    try:
        print()
        print("Starting ingest tool...")
        for i in range(width + 1):
            pct = i / width
            bar = "[" + "#" * i + "-" * (width - i) + "]"
            print(f"\rInitializing {bar} {pct*100:5.1f}%", end="", flush=True)
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
    "texture",
    "material/texture",
    "buildings",
    "layouts",
    "fixture",
    "object",
    "procedural",
    "location",
    "vehicle",
    "vfx",
}
PREVIEW_LABELS = {
    "furniture": {
        "Mood": "Subcategory Path",
        "Author": "Model Name",
        "Writer": "Brand",
        "Album": "Collection",
        "Genre": "Primary Color/Material",
        "People": "Usage Location",
        "Company": "Shape Form",
        "Period": "Period",
        "Artist": "Size",
        "Title": "Vendor Name",
        "From": "From",
        "Manager": "Category",
    },
    "vegetation": {
        "Mood": "Plant Type",
        "Author": "Approx. Height",
        "Writer": "Latin Name",
        "Album": "Common Name",
        "Genre": "Foliage Color",
        "People": "Growth Location",
        "Company": "Growth Form",
        "Period": "Seasonal Appearance",
        "Artist": "Size",
        "From": "From",
        "Manager": "Category",
    },
    "people": {
        "Mood": "Original Code Hint",
        "Author": "Gender",
        "Writer": "Ethnicity",
        "Album": "Age Group",
        "Genre": "Clothing Color",
        "People": "Scene Context",
        "Period": "Clothing Style",
        "Artist": "Pose / Activity",
        "From": "From",
        "Manager": "Category",
    },
    "material": {
        "Mood": "Material Name",
        "Genre": "Dominant Color",
        "Company": "Texture Pattern",
        "Period": "Material Category",
        "Artist": "Surface Finish",
        "From": "From",
        "Manager": "Category",
    },
    "buildings": {
        "Mood": "Subcategory",
        "Company": "Physical Form",
        "Period": "Primary Material",
        "Artist": "Size",
        "From": "From",
        "Manager": "Category",
    },
    "layouts": {
        "Mood": "Layout Type",
        "Writer": "Approx. Size",
        "People": "Room Type",
        "Period": "Layout Shape",
        "From": "From",
        "Manager": "Category",
    },
    "fixture": {
        "Mood": "Category",
        "Author": "Primary Description",
        "Writer": "Brand",
        "Album": "Material",
        "Genre": "Form",
        "People": "Usage Location",
        "Artist": "Size",
        "Title": "Vendor Name",
        "From": "From",
        "Manager": "Category",
    },
    "object": {
        "Author": "SubCategory",
        "Writer": "Brand",
        "Album": "Material",
        "Genre": "Form",
        "People": "Usage Location",
        "Artist": "Size",
        "Title": "Vendor Name",
        "From": "From",
        "Manager": "Category",
    },
    "procedural": {
        "Mood": "Type",
        "Author": "Description",
        "Company": "Software/Plugin",
        "From": "From",
        "Manager": "Category",
    },
    "location": {
        "Mood": "Category",
        "Author": "SubCategory",
        "Writer": "Width",
        "Album": "Length",
        "Genre": "Height",
        "People": "Location",
        "From": "From",
        "Manager": "Category",
    },
    "vehicle": {
        "Mood": "Type",
        "Author": "Model",
        "Writer": "Brand",
        "Genre": "Color",
        "Period": "Year",
        "Artist": "Size",
        "From": "From",
        "Manager": "Category",
    },
    "vfx": {
        "Mood": "Type",
        "Author": "Description",
        "Genre": "Style/Variant",
        "From": "From",
        "Manager": "Category",
    },
}
USER_LABELS: list[str] = []
# Loaded from manual/ingest_keywords.md (## CLIP Labels section).
AUTO_SUGGEST_LABELS: list[str] = _kw_clip_labels()


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
    _SECTION_HEADERS = {
        "Table", "Seating", "Lighting", "Storage", "Bed", "Sofa", "Fixtures",
        "Bathroom", "Kitchen", "Outdoor", "Street", "Bar", "Cafe", "Bedroom",
        "Gym", "Office", "Laundry", "Decor", "Furniture", "HVMC",
        "RoomDividers", "Sculpture",
    }
    if candidate_clean in _SECTION_HEADERS:
        candidate_clean = ""  # force keyword fallback below

    if candidate_clean and candidate_clean in allowed:
        return candidate_clean

    keyword_map = _kw_keyword_map()
    for needle, mapped in keyword_map:
        if needle in stem_lower and mapped in allowed:
            return mapped

    hint_model = sanitize_name_token(hints.get("model", ""))
    if hint_model in allowed:
        return hint_model

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
    if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
        raise ValueError(f"Unsupported image type: {image_path.suffix}")
    if archive_path.suffix.lower() not in ARCHIVE_EXTENSIONS:
        raise ValueError(f"Unsupported archive type: {archive_path.suffix}")
    if image_path.stem != archive_path.stem:
        raise ValueError(
            "Image and archive filenames must match exactly before the extension. "
            f"Got '{image_path.stem}' and '{archive_path.stem}'."
        )


def compute_crc32(file_path: Path) -> str:
    checksum = 0
    with file_path.open("rb") as file_handle:
        while chunk := file_handle.read(1024 * 1024):
            checksum = zlib.crc32(chunk, checksum)
    return f"{checksum & 0xFFFFFFFF:08X}"


def normalize_asset_type(raw: str) -> str:
    value = raw.strip().lower()
    if value == "material/texture":
        return "material"
    if value == "texture":
        return "material"
    return value


def prompt_session_context() -> str:
    print()
    print("Session context (optional): describe what you are importing.")
    print("  e.g. 'Importing bathroom faucets from Hansgrohe' or press Enter to skip.")
    raw = input("Context: ").strip()
    return raw


def parse_session_context(context: str) -> dict[str, str]:
    """Extract vendor/subcategory hints from free-text session description using gemma."""
    if not context:
        return {}
    allowed_subcats = sorted(load_furniture_subcategories())
    location_list = ", ".join(sorted(USAGE_LOCATION_ROOMS))
    prompt = (
        "Extract metadata hints from this session description. "
        "Return ONLY compact JSON with keys: vendor, subcategory, usage_location, brand. "
        "Use '-' for anything not mentioned. "
        f"subcategory must be one of: {', '.join(allowed_subcats)}. "
        f"usage_location must be one of: {location_list}. "
        f"Description: {context}"
    )       
    # Text model disabled; do not attempt remote text normalization.
    return {}



def prompt_asset_type() -> str:
    # Present a compact numbered menu and accept number, short abbreviation or full name.
    options = [
        ("furniture", "Furniture", "F"),
        ("vegetation", "Vegetation", "V"),
        ("people", "People", "P"),
        ("material", "Material/Texture", "M"),
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
    text = ollama_generate(prompt=prompt, timeout=45).splitlines()[0].strip()
    text = re.sub(r"[^A-Za-z0-9_]+", "", text)
    return text


def ollama_generate(prompt: str, image_path: Path | None = None, timeout: int = 90, model: str | None = None) -> str:
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
    # Show a spinner while waiting for the local Ollama model so the user
    # knows the process is active (not frozen).
    spinner_msg = "Vision model..." if image_path is not None else "Text model..."
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




def enrich_row_with_models(
    image_path: Path,
    source_stem: str,
    asset_type: str,
    hints: dict[str, str],
    row: dict[str, str],
    session_context: str = "",
    session_hints: dict[str, str] | None = None,
) -> dict[str, str]:
    """Use vision + text + web search passes to fill metadata columns.

    Pass 1 (vision): infer semantic fields from image + filename hints.
    Pass 2 (text):   normalize and correct using filename as ground truth.
    Pass 3 (web):    DuckDuckGo search to fill any remaining blank fields.
    """
    if asset_type != "furniture":
        return row

    schema_keys = [
        "subcategory",
        "model_name",
        "brand",
        "collection",
        "primary_material_or_color",
        "usage_location",
        "shape_form",
        "period",
        "size",
        "vendor_name",
    ]
    schema_text = ", ".join(schema_keys)

    vision_data: dict[str, str] = {}
    text_data: dict[str, str] = {}
    vision_error = ""
    text_error = ""

    allowed_subcats = sorted(load_furniture_subcategories())
    subcats_list = ", ".join(allowed_subcats)
    location_list = ", ".join(sorted(USAGE_LOCATION_ROOMS))

    session_hint_str = ""
    if session_context:
        session_hint_str = f"Session context from user: '{session_context}'. "
    sh = session_hints or {}

    vision_prompt = (
        "You are a strict furniture metadata extractor for search indexing. "
        f"{session_hint_str}"
        "Return ONLY compact JSON with these exact keys: "
        f"{schema_text}. "
        "STRICT rules: "
        "(1) Use '-' for ANY field you are not confident about — do NOT guess. "
        f"(2) subcategory MUST be one of these exact values: {subcats_list}. Pick the closest match."
        "(3) model_name must be the product model name — NOT codes like '11-33', NOT numbers alone. "
        "(3b) brand must be ONLY the manufacturer/maker name (e.g. 'Minotti', 'Cassina'). Do NOT combine the product model and brand into one string. "
        "(4) primary_material_or_color must describe actual material or color visible in image — NOT a collection name. "
        f"(5) usage_location MUST be one of: {location_list}. Use '-' if none apply."
        "(6) size ONLY if an explicit dimension appears in filename (e.g. 100x200mm) — otherwise '-'. "
        "(7) No extra keys. No explanation. "
        f"Filename stem: {source_stem}. "
        f"Parsed hints: model={hints.get('model','')}, collection={hints.get('collection','')}, "
        f"brand={hints.get('brand','')}, lead_desc={hints.get('lead_desc','')}."
    )
    try:
        vision_raw = ollama_generate(prompt=vision_prompt, image_path=image_path, timeout=180, model=OLLAMA_VISION_MODEL)
        vision_data = extract_json_payload(vision_raw)
    except Exception as exc:
        vision_error = str(exc).splitlines()[0][:80]

    # Pass 2 (text normalization) and Pass 3 (web search) removed per user request.
    # We'll rely solely on the vision model output and deterministic fallbacks.
    text_data = {}
    text_error = ""

    def pick(key: str, fallback: str = "-") -> str:
        tval = (text_data.get(key, "") or "").strip()
        vval = (vision_data.get(key, "") or "").strip()
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
    _ai_subcategory = normalize_furniture_subcategory(
        pick("subcategory", row.get("Mood", "-")), source_stem, hints
    )

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
    model_name = clean_display_case(pick_with_db("model_name", "Author", "-"))
    primary_material = clean_display_case(pick_with_db("primary_material_or_color", "Genre", "-"))
    shape_form = clean_display_case(pick_with_db("shape_form", "Company", "-"))
    period = clean_display_case(pick_with_db("period", "Period", "-"))
    size = pick_with_db("size", "Artist", "-")
    # Vendor: AI pick → DB Title → brand fallback
    vendor_name = clean_display_case(pick("vendor_name", ""))
    if not vendor_name or vendor_name == "-":
        db_vendor = db_get("Title")
        vendor_name = clean_display_case(db_vendor) if db_vendor else clean_display_case(brand)
    # Carry over Rating from DB if present
    if db_row.get("Rating", "").strip() and db_row["Rating"].strip() not in ("-", "0", ""):
        row["Rating"] = db_row["Rating"].strip()
    # Carry over URL from DB if present
    if db_row.get("URL", "").strip() and db_row["URL"].strip() not in ("-", ""):
        row["URL"] = db_row["URL"].strip()

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

    # Model name: reject if it is a long descriptive phrase (5+ words) — likely the whole filename.
    if model_name and model_name != "-":
        word_count = len(model_name.split())
        if word_count >= 5:
            model_name = "-"
        else:
            # Also reject if it starts with a room/location word (descriptor, not a product name).
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
    if (not model_name or model_name == "-") and brand and brand != "-":
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

    row["Mood"] = build_mood_hierarchy(subcategory) if subcategory and subcategory != "" else "-"
    row["Author"] = model_name if model_name else "-"
    row["Writer"] = brand if brand else "-"
    row["Album"] = collection if collection else "-"
    row["Genre"] = primary_material if primary_material else "-"
    row["People"] = usage_location if usage_location else "-"
    row["Company"] = shape_form if shape_form else "-"
    row["Period"] = period if period else "-"
    row["Artist"] = size if size else "-"
    row["Title"] = vendor_name if vendor_name and vendor_name != "-" else (brand or "-")
    # Ensure the Manager field includes the category while preserving any existing
    # parse/source trace that may already be stored there.
    cur_manager = row.get("Manager", "-")
    if not cur_manager or cur_manager == "-":
        row["Manager"] = "Furniture"
    else:
        if "Furniture" not in cur_manager:
            row["Manager"] = f"Furniture;{cur_manager}"

    # Keep deterministic parse as fallback and attach diagnostics non-destructively.
    diagnostics: list[str] = []
    if vision_error:
        diagnostics.append(f"vision_error={vision_error}")
    if text_error:
        diagnostics.append(f"text_error={text_error}")
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
    mood_value = mood_hierarchy_leaf(row.get("Mood", "")) or row.get("Mood", "")
    if asset_type == "furniture":
        # User preference: for furniture, filename should only contain subcategory
        # (plus CRC added later), while other mapped data stays in index columns.
        preferred = [mood_value]
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

    # For furniture, keep deterministic subcategory-only naming.
    if asset_type == "furniture":
        return deterministic

    # Try Qwen cleanup first for noisy names; fallback to deterministic semantic naming.
    try:
        qwen_name = clean_name_with_qwen(
            asset_type=asset_type,
            source_stem=fallback,
            mapped_subcategory=row.get("Mood", ""),
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
    row["Subject"] = archive_path.name
    row["CRC-32"] = crc32_value

    if asset_type == "furniture":
        # Furniture mapping from everything_columnmapping.md:
        # Mood=Subcategory, Author=Model Name, Writer=Brand, Album=Collection,
        # People=Usage Location, Artist=Size.
        row["Mood"] = sanitize_name_token(hints["model"] or hints["lead_desc"])
        row["Author"] = "-"
        row["Writer"] = clean_display_case(hints["brand"] or hints["brand_raw"])
        row["Album"] = clean_display_case(hints["collection"])
        row["People"] = clean_display_case(hints["lead_desc"])
        row["Artist"] = hints["size"]
        row["Title"] = clean_display_case(hints["brand"] or hints["brand_raw"])
        row["From"] = "-"
        row["Manager"] = "Furniture"
    elif asset_type == "vegetation":
        row["Mood"] = clean_display_case(hints["lead_desc"] or hints["model"])
        row["Author"] = hints["size"]
        row["Writer"] = clean_display_case(hints["model"])
        row["Album"] = clean_display_case(hints["collection"] or hints["lead_desc"])
        row["Artist"] = hints["size"]
        row["From"] = "-"
        row["Manager"] = "Vegetation"
    elif asset_type == "people":
        row["Mood"] = clean_display_case(hints["lead_desc"])
        row["Author"] = clean_display_case(hints["model"])
        row["Writer"] = clean_display_case(hints["collection"])
        row["Artist"] = hints["size"]
        row["From"] = "-"
        row["Manager"] = "People"
    elif asset_type == "material":
        row["Mood"] = clean_display_case(hints["lead_desc"] or hints["model"])
        row["Genre"] = clean_display_case(hints["collection"])
        row["Company"] = clean_display_case(hints["model"])
        row["Period"] = clean_display_case("Material Category")
        row["Artist"] = hints["size"]
        row["From"] = "-"
        row["Manager"] = "Material"
    elif asset_type == "buildings":
        row["Mood"] = clean_display_case(hints["lead_desc"])
        row["Company"] = clean_display_case(hints["model"])
        row["Period"] = clean_display_case(hints["collection"])
        row["Artist"] = hints["size"]
        row["From"] = "-"
        row["Manager"] = "Buildings"
    elif asset_type == "layouts":
        row["Mood"] = clean_display_case(hints["lead_desc"])
        row["Writer"] = hints["size"]
        row["People"] = clean_display_case(hints["model"])
        row["Period"] = clean_display_case(hints["collection"])
        row["From"] = "-"
        row["Manager"] = "Layouts"

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
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        existing_headers = reader.fieldnames or []
        rows = list(reader)

    migrated = False
    new_rows: list[dict[str, str]] = []
    for old in rows:
        row = {k: (v if v not in (None, "") else "-") for k, v in old.items()}
        comment_val = (row.get("Comment") or "").strip()
        manager_val = (row.get("Manager") or "").strip()
        mood_val = (row.get("Mood") or "").strip()
        # If comment contains a src trace and manager doesn't, move it.
        if comment_val and comment_val != "-" and "src=" in comment_val and "src=" not in manager_val:
            if not manager_val or manager_val == "-":
                row["Manager"] = comment_val
            else:
                row["Manager"] = f"{manager_val};{comment_val}"
            row["Comment"] = "-"
            migrated = True
        mood_path = build_mood_hierarchy(mood_val)
        if mood_path != mood_val and mood_path != "-":
            row["Mood"] = mood_path
            migrated = True
        new_rows.append(row)

    # If headers mismatch or migration happened, rewrite file with canonical headers.
    if existing_headers != EFU_HEADERS or migrated:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=EFU_HEADERS)
            writer.writeheader()
            for old in new_rows:
                merged = {header: "-" for header in EFU_HEADERS}
                for key, value in old.items():
                    if key in merged:
                        merged[key] = value if value not in (None, "") else "-"
                writer.writerow(merged)


def append_metadata_row(path: Path, row: dict[str, str]) -> None:
    ensure_metadata_file(path)
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
    print("Mapped preview:")
    label_map = PREVIEW_LABELS.get(asset_type, {})
    preview_rows: list[tuple[str, str]] = [("Thumbnail Filename", row.get("Filename", "-") or "-")]
    preview_rows.append(("Tags", row.get("Tags", "-") or "-"))
    for field, semantic in label_map.items():
        value = row.get(field, "-") or "-"
        preview_rows.append((semantic, value))
    preview_rows.append(("Related Archive", row.get("Subject", "-") or "-"))
    preview_rows.append(("CRC-32", row.get("CRC-32", "-") or "-"))
    preview_rows.append(("Trace", row.get("Comment", "-") or "-"))

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
    # Use Ollama Qwen model (primary path)
    img_b64 = base64.b64encode(image_path.read_bytes()).decode('utf-8')
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": "Return one short CamelCase product label describing the main object. No explanation.",
        "images": [img_b64],
        "stream": False,
    }
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    spinner = _Spinner(f"Vision label: {image_path.name}")
    spinner.start()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    finally:
        try:
            spinner.stop()
        except Exception:
            pass
    resp_text = body.get("response", "").strip()
    if not resp_text:
        raise RuntimeError("Qwen returned no label")
    return to_camel_case(resp_text.splitlines()[0]), 1.0, "qwen-ollama"


def move_pair(
    image_path: Path,
    archive_path: Path,
    new_base_name: str,
    image_dir: Path | None = None,
    archive_dir: Path | None = None,
) -> tuple[Path, Path]:
    image_target, archive_target, _ = ensure_unique_targets(
        new_base_name,
        image_path.suffix.lower(),
        archive_path.suffix.lower(),
        image_dir=image_dir,
        archive_dir=archive_dir,
    )
    moved_image = Path(shutil.move(str(image_path), str(image_target)))
    moved_archive = Path(shutil.move(str(archive_path), str(archive_target)))
    return moved_image, moved_archive


def main() -> None:
    try:
        # command-line flags
        dry_run = False
        quick = False
        auto_yes = False
        asset_type: str | None = None
        # Allow non-interactive invocation with multiple file arguments (pairs)
        def process_pair(
            image_path: Path,
            archive_path: Path,
            asset_type: str,
            dry_run: bool = False,
            quick: bool = False,
            auto_yes: bool = False,
            session_context: str = "",
            session_hints: dict[str, str] | None = None,
        ) -> None:
            try:
                validate_inputs(image_path, archive_path)
                print(f"Processing pair: {image_path} + {archive_path}")
                if quick:
                    label = to_camel_case(image_path.stem)
                    confidence = 1.0
                    label_source = "quick"
                else:
                    label, confidence, label_source = classify_image(image_path)

                try:
                    crc32_value = compute_crc32(archive_path)
                except FileNotFoundError:
                    if dry_run:
                        crc32_value = "MISSING"
                    else:
                        raise

                # Build initial row with a placeholder filename, then derive a shorter base name
                # from mapped values so filename does not repeat metadata already captured in columns.
                hints = parse_filename_hints(image_path.stem)
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
                metadata_row = dict(temp_row)
                metadata_row["Filename"] = image_target.name
                metadata_row["Subject"] = archive_target.name

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
                        metadata_row["Title"] = vendor_clean

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
                    image_dir=image_dir,
                    archive_dir=archive_dir,
                )
                append_metadata_row(METADATA_EFU_PATH, metadata_row)
                print(f"Label: {label} | Source: {label_source} | Confidence: {confidence:.2%}")
                print(f"CRC-32: {crc32_value}")
                print(f"Image moved to: {moved_image}")
                print(f"Archive moved to: {moved_archive}")
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
            print("Usage: python tools/ingest_asset.py [--dry-run] [--quick] [--yes] --asset-type=furniture <image> <archive> ...")
            print("Use -h or --help to see detailed flags and examples.")
        flags = ["--dry-run", "--quick"]
        clean_args: list[str] = []
        for a in argv:
            if a == "--dry-run":
                dry_run = True
            elif a == "--quick":
                quick = True
            elif a in {"--yes", "-y"}:
                auto_yes = True
            elif a.startswith("--asset-type="):
                asset_type = normalize_asset_type(a.split("=", 1)[1])
            else:
                clean_args.append(a)

        if asset_type and asset_type not in ASSET_TYPES:
            raise ValueError(f"Unsupported asset type: {asset_type}")

        if not asset_type:
            asset_type = prompt_asset_type()

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
                        print(f"Skipping stem '{stem}': expected 2 files, found {len(items)}")
                        processed += 1
                        _print_progress(processed, total)
                        continue
                    a, b = items
                    # determine which is image and which is archive
                    if a.suffix.lower() in IMAGE_EXTENSIONS and b.suffix.lower() in ARCHIVE_EXTENSIONS:
                        process_pair(a, b, asset_type=asset_type, dry_run=dry_run, quick=quick, auto_yes=auto_yes, session_context=session_context, session_hints=session_hints)
                    elif b.suffix.lower() in IMAGE_EXTENSIONS and a.suffix.lower() in ARCHIVE_EXTENSIONS:
                        process_pair(b, a, asset_type=asset_type, dry_run=dry_run, quick=quick, auto_yes=auto_yes, session_context=session_context, session_hints=session_hints)
                    else:
                        print(f"Skipping stem '{stem}': could not identify image/archive pair ({a}, {b})")
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
            paste_stems: dict[str, list[Path]] = defaultdict(list)
            for raw_path in pasted_lines:
                p = Path(raw_path)
                if p.exists() and p.is_file():
                    paste_stems[p.stem].append(p)
                else:
                    print(f"  Skipping (not found): {raw_path}")

            paste_items = list(paste_stems.items())
            total = len(paste_items)
            if total == 0:
                print("No valid files found in pasted paths.")
                return

            print(f"Processing {total} pair(s)...")
            processed = 0
            for stem, items in paste_items:
                if len(items) != 2:
                    print(f"  Skipping '{stem}': expected 2 files, found {len(items)}")
                    processed += 1
                    _print_progress(processed, total)
                    continue
                a, b = items
                if a.suffix.lower() in IMAGE_EXTENSIONS and b.suffix.lower() in ARCHIVE_EXTENSIONS:
                    process_pair(a, b, asset_type=asset_type, dry_run=dry_run, quick=quick, auto_yes=auto_yes, session_context=session_context, session_hints=session_hints)
                elif b.suffix.lower() in IMAGE_EXTENSIONS and a.suffix.lower() in ARCHIVE_EXTENSIONS:
                    process_pair(b, a, asset_type=asset_type, dry_run=dry_run, quick=quick, auto_yes=auto_yes, session_context=session_context, session_hints=session_hints)
                else:
                    print(f"  Skipping '{stem}': could not identify image/archive pair")
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
