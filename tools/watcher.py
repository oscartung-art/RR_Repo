#!/usr/bin/env python3
# NOTE: This file will be renamed to watcher.py by automated update

"""
clipboard_asset_watcher.py — Background daemon to handle asset management commands from clipboard.

Runs in background, monitors clipboard for commands in the format:
    <file-path> <action>[:] [arguments]
    OR multiple files: "path1" "path2" "path3" action[:] [arguments]
    OR with pipes between quoted files: "path1" | "path2" | "path3" action[:] [arguments]

Supported actions:
- enrich:    AI-enrich metadata (brand, subject, color, etc.) for existing asset.
             For new assets: specify asset_type to create entry: "path" enrich furniture
             Multiple files: "path1" "path2" enrich furniture creates all new entries
- audit:    Audit .metadata.efu file and remove entries for files no longer in folder
- create:    Extract images from PDF and create .metadata.efu entries (like ingest_schedule)
- set:       Set one or more metadata fields (e.g. "path set Rating=99 Tags=lighting;modern")

Run:
    python tools/clipboard_asset_watcher.py [--dry-run]

Stop with Ctrl+C.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path
from typing import Tuple, Optional, List, Dict

# ---------------------------------------------------------------------------
# Windows-specific imports — this is a Windows-only tool
# ---------------------------------------------------------------------------
try:
    import win32gui
    import winsound
    import pyperclip
    # Disable win10toast due to known bugs with classAtom attribute
    # from win10toast import ToastNotifier
    HAS_TOAST = False
except ImportError as exc_main:
    sys.exit(
        f"[clipboard-watcher] Missing required package: {exc_main}\n"
        "Install with: pip install pywin32 pyperclip"
    )

# Try to import send2trash for safe deletion to Recycle Bin
try:
    from send2trash import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    HAS_SEND2TRASH = False
    send2trash = None

# ---------------------------------------------------------------------------
# Import existing functionality from RR tools
# ---------------------------------------------------------------------------

# Add parent directory to path so we can import project modules
# When running as python tools/clipboard_asset_watcher.py, tools/ is on the same level
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env file if it exists (for API keys and configuration)
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    try:
        with open(_env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    if key not in os.environ:  # Don't override existing env vars
                        os.environ[key] = value
    except Exception:
        pass  # Silently ignore .env loading errors

# Import from same tools directory
from edit_efu_metadata import (
    FIELD_ALIASES,
    resolve_field,
    update_efu,
    VALID_RATINGS,
    _load_efu,
    _write_efu,
)
from move_delete_assets import _row_basename
from move_delete_assets import (
    _remove_from_efu,
    _remove_from_central_efu,
    CENTRAL_EFU,
    _find_archive,
    ASSET_EXTENSIONS,
    IMAGE_EXTENSIONS,
)
from ingest_schedule import (
    _find_header_xrefs,
    extract_page_images,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CHECK_INTERVAL = 0.2  # seconds — responsive without CPU hammering
DRY_RUN = False

# Asset type abbreviations — map short prefixes/abbreviations to full asset types
# From actual ASSET_TYPES in ingest_asset.py
ASSET_TYPE_ABBREVIATIONS = {
    "fix": "fixture",
    "veg": "vegetation",
    "fur": "furniture",
    "obj": "object",
    "peo": "people",
    "mat": "material",
    "lay": "layouts",
    "veh": "vehicle",
    "vfx": "vfx"
}

# ---------------------------------------------------------------------------
# Runtime State
# ---------------------------------------------------------------------------
_last_seen: str = ""

# For description-based enrichment state tracking
_waiting_for_description: bool = False
_pending_image_path: Optional[Path] = None
_last_paste_time: float = 0.0
_DESCRIPTION_TIMEOUT = 300.0  # 5 minutes

# Constants for description detection
_MIN_DESC_LENGTH = 50         # Minimum characters to be considered a description
_MAX_DESC_LENGTH = 2000      # Maximum reasonable description length

# ---------------------------------------------------------------------------
# Helpers - Audio feedback
# ---------------------------------------------------------------------------
def _notify(kind, message=""):
    """Show Windows toast notification instead of beep."""
    if not HAS_TOAST:
        # Fallback to beep if win10toast not available
        mapping = {
            "start":    winsound.MB_ICONQUESTION,
            "success":  winsound.MB_ICONASTERISK,
            "error":    winsound.MB_ICONHAND,
            "no_match": winsound.MB_ICONEXCLAMATION,
        }
        try:
            winsound.MessageBeep(mapping.get(kind, winsound.MB_ICONASTERISK))
        except Exception:
            pass
        return
    
    # Show toast notification
    titles = {
        "start":    "⏳ Processing...",
        "success":  "✓ Success",
        "error":    "✗ Error",
        "no_match": "⚠ Not Found",
    }
    
    title = titles.get(kind, "Clipboard Watcher")
    if not message:
        message = {
            "start":    "Processing asset command",
            "success":  "Operation completed",
            "error":    "Operation failed",
            "no_match": "File or entry not found",
        }.get(kind, "Notification")
    
    try:
        toaster = ToastNotifier()
        toaster.show_toast(
            title,
            message,
            duration=3,
            threaded=True,
        )
    except Exception:
        # Fallback to beep on error
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

# Backward compatibility alias
_beep = lambda kind: _notify(kind)


def _looks_like_description(text: str) -> bool:
    """Determine if text looks like an asset description (not a command)."""
    text = text.strip()

    # Skip empty or very short text
    if len(text) < _MIN_DESC_LENGTH or len(text) > _MAX_DESC_LENGTH:
        return False

    # Skip if it looks like a command (contains action keywords)
    if _looks_like_command(text):
        return False

    # Skip if it contains file path patterns
    if re.search(r'[A-Z]:[\\/].*', text, re.IGNORECASE) or re.search(r'\.(jpg|jpeg|png|pdf|json|efu)$', text.lower()):
        return False

    # Looks like a description if it has sentence structure
    has_sentence = re.search(r'[A-Z][^.!?]*[.!?]', text)  # Capital letter followed by sentence ending
    has_multiline = text.count('\n') >= 1
    has_keywords = any(keyword in text.lower() for keyword in ['designed', 'designed by', 'dimensions', 'materials', 'features', 'specifications', 'collection', 'manufactured', 'brand', 'model'])

    return has_sentence or has_multiline or has_keywords


def _is_image_file(path: Path) -> bool:
    """Check if a path is an image file (by extension)."""
    return path.is_file() and path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']


def _is_single_image_path(text: str) -> bool:
    """Check if text is just a single image file path (not a command)."""
    text = text.strip()
    if not text:
        return False

    # If it has action keywords, it's a command
    if _looks_like_command(text):
        return False

    # Try to parse as a single path
    try:
        # Strip quotes (common in paths)
        stripped = text.strip('"').strip("'")
        path = Path(stripped)
        if path.is_file() and _is_image_file(path):
            return True
    except Exception:
        pass

    return False


def resolve_asset_type_abbreviation(abbr: str) -> str:
    """Resolve asset type abbreviation to full name.

    Supports:
    - Exact matches in ASSET_TYPE_ABBREVIATIONS (e.g., "fix" → "fixture")
    - First three letters of any asset type (e.g., "fur" → "furniture")
    - Case-insensitive matching
    """
    abbr_lower = abbr.strip().lower()

    # Check exact mapping first
    if abbr_lower in ASSET_TYPE_ABBREVIATIONS:
        return ASSET_TYPE_ABBREVIATIONS[abbr_lower]

    # Fall back to checking if it's a valid 3-letter prefix of any known asset type
    # Build a temporary map of 3-letter prefixes to full types from the known abbreviations
    prefix_map = {full[:3].lower(): full for full in ASSET_TYPE_ABBREVIATIONS.values()}
    if abbr_lower in prefix_map:
        return prefix_map[abbr_lower]

    # If no match, return as-is (allow full asset types to be specified)
    return abbr

# ---------------------------------------------------------------------------
# Command Parsing
# ---------------------------------------------------------------------------
def _looks_like_command(text: str) -> bool:
    """Cheap heuristic: does this look like a file path + command?"""
    low = text.lower().strip()
    # Must have a drive letter (Windows) or path separator
    if ":" not in low and "\\" not in low and "/" not in low:
        return False

    # Check if any token (which could be the last one) is an action
    tokens = low.split()
    if not tokens:
        return False

    for token in tokens:
        cleaned = token.rstrip(':')
        if cleaned in ["enrich", "audit", "create", "set", "describe"]:
            return True
    return False

def _extract_all_after_keyword(text: str, keyword: str) -> Optional[str]:
    """Extract everything after a keyword (including after colon if present)."""
    idx = text.lower().find(keyword)
    if idx >= 0:
        keyword_len = len(keyword)
        result = text[idx + keyword_len:].strip()
        # Skip any colon or whitespace right after the keyword
        if result.startswith(':'):
            result = result[1:].strip()
        return result
    return None


def parse_command(text: str) -> Tuple[Optional[list[Path]], Optional[str], Optional[List[Tuple[str, str]]]]:
    """
    Parse command from clipboard text.
    Accepts:
    - Single path: "path action"
    - Multiple paths: "path1" | "path2" | "path3" action args
    - Multiple paths whitespace-separated: path1 path2 action args
    Strips: Everything bracketed [ ... ] (added by Everything when copying images)
    Returns: (list_of_file_paths, action, args) where args is list of (canonical_field, value) for 'set'.
    """
    text = text.strip()
    # Strip out Everything's bracketed prefix/suffix like "[Image: ...]" or "[Image #1]"
    # BUT preserve brackets that are part of the filename (when path is quoted)
    # Strategy: Only remove brackets that are NOT inside quoted strings
    
    # First, protect quoted strings by temporarily replacing them
    quoted_parts = re.findall(r'"([^"]+)"', text)
    placeholder_map = {}
    for i, qp in enumerate(quoted_parts):
        placeholder = f"__QUOTED_{i}__"
        placeholder_map[placeholder] = qp
        text = text.replace(f'"{qp}"', placeholder, 1)
    
    # Now remove brackets from unquoted parts only
    text = re.sub(r'\[[^\]]*\]', '', text).strip()
    
    # Restore quoted strings (with their original brackets intact)
    for placeholder, original in placeholder_map.items():
        text = text.replace(placeholder, f'"{original}"')
    
    # Replace angle brackets with spaces instead of removing them entirely
    # This handles paths wrapped in <> without losing content
    text = text.replace('<', ' ').replace('>', ' ').strip()

    # Support flag-style set commands pasted from terminal, e.g.:
    # --field 4 --value "Yellow" "G:\\DB\\img.jpg"
    import shlex
    try:
        tokens = shlex.split(text)
    except Exception:
        tokens = text.split()

    if tokens and any(t in ('-f', '--field', '-v', '--value') or t.startswith('--field=') or t.startswith('--value=') for t in tokens):
        # Parse simple flag-style: --field/-f and --value/-v. Remaining tokens are paths.
        opts: list[tuple[str, str]] = []
        paths_tokens: list[str] = []
        i = 0
        while i < len(tokens):
            t = tokens[i]
            if t in ('-f', '--field'):
                if i + 1 < len(tokens):
                    opts.append(('field', tokens[i+1]))
                    i += 2
                    continue
                else:
                    return None, None, None
            if t.startswith('--field='):
                opts.append(('field', t.split('=', 1)[1]))
                i += 1
                continue
            if t in ('-v', '--value'):
                if i + 1 < len(tokens):
                    opts.append(('value', tokens[i+1]))
                    i += 2
                    continue
                else:
                    return None, None, None
            if t.startswith('--value='):
                opts.append(('value', t.split('=', 1)[1]))
                i += 1
                continue
            if t in ('--dry-run', '-n'):
                # ignore for now, watcher DRY_RUN handled via CLI when starting
                i += 1
                continue
            # Otherwise treat as path
            paths_tokens.append(t)
            i += 1

        if not paths_tokens:
            return None, None, None

        # Build field/value pairs
        field_vals = [v for k, v in opts if k == 'field']
        value_vals = [v for k, v in opts if k == 'value']
        pairs: list[tuple[str, str]] = []
        if field_vals and value_vals:
            if len(field_vals) == len(value_vals):
                for f, v in zip(field_vals, value_vals):
                    pairs.append((resolve_field(f), v))
            else:
                # Use first field for first value if counts mismatch
                pairs.append((resolve_field(field_vals[0]), value_vals[0]))
        else:
            # Require both --field and --value
            return None, None, None

        # Convert paths to Path objects
        try:
            path_objs = [Path(p).absolute() for p in paths_tokens]
        except Exception:
            return None, None, None

        return path_objs, 'set', pairs

    all_words = text.split()

    if len(all_words) < 2:
        return None, None, None

    # Find the last word that is an action keyword
    # This allows multiple paths before the action (supports spaces in paths when quoted)
    action_index = -1
    for i, word in enumerate(reversed(all_words)):
        candidate = word.lower().rstrip(':')
        if candidate in ["enrich", "audit", "create", "set"]:
            action_index = len(all_words) - 1 - i
            break

    if action_index == -1:
        return None, None, None

    # All words before action_index are paths (may be quoted)
    # All words after action_index are arguments
    path_words = all_words[:action_index]
    action_raw = all_words[action_index].lower().rstrip(':')
    args_words = all_words[action_index+1:]
    args_str = " ".join(args_words)

    # Collect paths: extract all quoted paths (handles spaces in filenames)
    paths_text = " ".join(path_words)
    # Remove any angle brackets < > around the entire paths list
    paths_text = paths_text.strip('<>')

    # Find all "..." quoted strings - these are individual paths
    quoted_paths = re.findall(r'"([^"]+)"', paths_text)
    if quoted_paths:
        # We have quoted paths - use ONLY those (ignore unquoted search paths from Everything)
        path_strs = quoted_paths
    else:
        # No quotes - split on pipe or whitespace
        # Replace pipes with spaces first
        temp_text = paths_text.replace('|', ' ').strip()
        path_strs = temp_text.split()

    # Filter out empty strings, pipe symbols, and paths with invalid characters
    path_strs = [p.strip() for p in path_strs
                 if p.strip() and p.strip() != '|' and '<' not in p and '>' not in p]
    if not path_strs:
        return None, None, None

    # Normalize all paths
    # Use absolute() instead of resolve() because resolve() converts mapped drives to UNC
    # which can cause accessibility issues even when the file exists. The original drive letter
    # preserved by absolute() works better for network share mappings.
    try:
        paths = []
        for p_str in path_strs:
            path = Path(p_str).absolute()
            paths.append(path)
        if not paths:
            return None, None, None
    except Exception:
        return None, None, None

    # Parse arguments based on action
    if action_raw == "set":
        if not args_str:
            return paths, "set", []
        # Parse key=value pairs
        pairs = []
        # Split on whitespace, but handle quoted values (simple approach)
        tokens = re.findall(r'([^\s=]+)=("[^"]+"|\'[^\']+\'|\S+)', args_str)
        for field_raw, value in tokens:
            value = value.strip('"\'')
            field = resolve_field(field_raw)
            pairs.append((field, value))
        return paths, "set", pairs if pairs else None
    elif action_raw == "enrich":
        # For enrich, allow optional trailing asset_type argument
        # Format: "enrich furniture" or "enrich:furniture" or "enrich fur" (abbreviation)
        if args_str and args_str.strip():
            # Return as single tuple (any key, we just care about the value in handler)
            asset_type = args_str.strip().lower()
            resolved_asset_type = resolve_asset_type_abbreviation(asset_type)
            if resolved_asset_type != asset_type:
                print(f"[clipboard-watcher] Resolved asset type: {asset_type} -> {resolved_asset_type}")
            return paths, "enrich", [("asset_type", resolved_asset_type)]
        return paths, "enrich", []
    elif action_raw == "describe":
        # Special handling for describe command - treat remaining text as description
        return paths, "describe", [("description", args_str)]
    elif action_raw in ["audit", "create"]:
        return paths, action_raw, []
    else:
        return None, None, None

# ---------------------------------------------------------------------------
# Action Handlers
# ---------------------------------------------------------------------------
def _handle_describe_enrich(image_path: Path, description_text: str) -> bool:
    """Enrich asset with metadata from description text using existing AI pipeline."""
    print(f"\n[clipboard-watcher] DESCRIBE-ENRICH {image_path}")
    print(f"  Description length: {len(description_text)} characters")

    if not image_path.exists() or not _is_image_file(image_path):
        print(f"[error] Not a valid image file: {image_path}")
        _beep("error")
        return False

    efu_path = image_path.parent / ".metadata.efu"
    fieldnames: list[str]
    rows: list[dict]
    existing_row = None
    row_index = -1

    if efu_path.exists():
        fieldnames, rows = _load_efu(efu_path)
        target_basename = image_path.name.lower()
        for i, row in enumerate(rows):
            if _row_basename(row) == target_basename:
                existing_row = row
                row_index = i
                break
    else:
        from ingest_schedule import EFU_FIELDNAMES
        fieldnames = EFU_FIELDNAMES
        rows = []

    # Auto-detect asset type
    try:
        from ingest_asset import detect_root_from_name
        asset_type = detect_root_from_name(image_path.name)
        if not asset_type:
            asset_type = "material"
        print(f"  Asset type (auto-detected): {asset_type}")
    except Exception as e:
        print(f"  [warn] Failed to detect asset type: {e}")
        asset_type = "material"

    # Run AI enrichment with description as sidecar text
    try:
        from ingest_asset import infer_metadata_fields, enrich_row_with_models
        print(f"  Running AI enrichment with description...")
        _beep("start")

        metadata = infer_metadata_fields(
            asset_type=asset_type,
            source_stem=image_path.stem,
            image_path=image_path,
            sidecar_text=description_text
        )

        enriched_row = enrich_row_with_models(
            image_path=image_path,
            source_stem=image_path.stem,
            asset_type=asset_type,
            hints={},
            row=existing_row.copy() if existing_row else {},
            raw_sidecar_text=description_text
        )

        # Set Filename field (critical for EFU)
        enriched_row["Filename"] = image_path.name

        if existing_row:
            # Update existing row
            rows[row_index] = enriched_row
            print(f"  ✓ Updated existing entry")
        else:
            # Add new row
            rows.append(enriched_row)
            print(f"  ✓ Created new entry")

        # Write EFU
        _write_efu(efu_path, fieldnames, rows)
        print(f"  ✓ EFU saved: {efu_path}")

        _beep("success")
        return True

    except Exception as e:
        print(f"[error] Enrichment failed: {e}")
        import traceback
        traceback.print_exc()
        _beep("error")
        return False


def _handle_enrich(file_paths: list[Path], args: list[Tuple[str, str]] | None = None) -> bool:
    """Enrich metadata for asset(s).
    
    Usage modes:
      1. Single image: "G:\\DB\\asset.jpg" enrich furniture
      2. Multiple images with JSON: "img1.jpg" "img2.jpg" "data.json" enrich
      3. Folder with JSON: "G:\\DB\\folder\\" "data.json" enrich
    
    JSON format (keyed by code/filename stem):
    {
      "PL-01": {
        "subject": "Material/PlasticLaminate",
        "title": "HC9954T",
        "brand": "Formica",
        "color": "White Oak",
        "location": "General Wall Panel"
      },
      ...
    }
    """
    # Separate JSON file from image paths
    json_path = None
    image_paths = []
    
    for fp in file_paths:
        if fp.suffix.lower() == ".json":
            json_path = fp
        elif fp.is_dir():
            # Expand directory to all jpg/png files
            image_paths.extend(fp.glob("*.jpg"))
            image_paths.extend(fp.glob("*.png"))
        else:
            image_paths.append(fp)
    
    # JSON batch enrich mode (optional)
    if json_path:
        return _enrich_batch_with_json(image_paths, json_path)
    
    # Batch AI enrichment (no JSON - use normal AI enrichment for each)
    if len(image_paths) > 1:
        return _enrich_batch_ai(image_paths, args)
    
    # Single file enrichment (original behavior)
    file_path = image_paths[0]
    
    # Extract optional asset_type argument
    asset_type: str | None = None
    if args and len(args) > 0:
        asset_type = args[0][1].lower().strip()

    print(f"\n[clipboard-watcher] ENRICH {file_path}")

    if not file_path.exists():
        print(f"[error] File not found: {file_path}")
        _beep("error")
        return False

    # Route based on file type
    if file_path.suffix.lower() == ".pdf":
        return _enrich_pdf(file_path, asset_type)
    else:
        return _enrich_image(file_path, asset_type)


def _enrich_batch_ai(image_paths: list[Path], args: list[tuple]) -> bool:
    """Enrich multiple images using AI (no JSON - original behavior)."""
    from edit_efu_metadata import _write_efu, _load_efu
    from ingest_asset import infer_metadata_fields, enrich_row_with_models
    
    # Extract optional asset_type argument
    asset_type: str | None = None
    if args and len(args) > 0:
        asset_type = args[0][1].lower().strip()
    
    print(f"\n[clipboard-watcher] BATCH AI ENRICH")
    print(f"  Images: {len(image_paths)}")
    if asset_type:
        print(f"  Asset type: {asset_type}")
    
    _beep("start")
    
    success_count = 0
    error_count = 0
    
    for file_path in image_paths:
        if not file_path.exists():
            print(f"  ✗ Not found: {file_path.name}")
            error_count += 1
            continue
        
        try:
            # Auto-detect asset type if not provided
            if not asset_type:
                from ingest_asset import detect_root_from_name
                detected = detect_root_from_name(file_path.name)
                current_type = detected if detected else "material"
            else:
                current_type = asset_type
            
            # Get EFU path for this image
            efu_path = file_path.parent / ".metadata.efu"
            
            # Load existing EFU (or start fresh)
            if efu_path.exists():
                fieldnames, rows = _load_efu(efu_path)
            else:
                from ingest_schedule import EFU_FIELDNAMES
                fieldnames = EFU_FIELDNAMES
                rows = []
            
            # Check if row exists
            existing_row = None
            row_index = -1
            for i, r in enumerate(rows):
                if r.get("Filename") == file_path.name:
                    existing_row = r
                    row_index = i
                    break
            
            # Run AI enrichment
            source_stem = file_path.stem
            metadata = infer_metadata_fields(
                current_type,
                source_stem,
                image_path=file_path,
                sidecar_text=""
            )
            enriched_row = enrich_row_with_models(
                file_path,
                source_stem,
                current_type,
                metadata,
                existing_row.copy() if existing_row else {}
            )
            
            # Set Filename field
            enriched_row["Filename"] = file_path.name
            
            # Update or append
            if existing_row:
                rows[row_index] = enriched_row
            else:
                rows.append(enriched_row)
            
            # Write back to EFU
            _write_efu(efu_path, fieldnames, rows)
            
            print(f"  ✓ {file_path.name} ({current_type})")
            success_count += 1
            
        except Exception as exc:
            print(f"  ✗ {file_path.name}: {exc}")
            error_count += 1
    
    # Summary
    print(f"\n  Enriched: {success_count}/{len(image_paths)}")
    if error_count > 0:
        print(f"  Errors: {error_count}")
        _beep("error")
        return False
    else:
        _beep("success")
        return True


def _enrich_batch_with_json(image_paths: list[Path], json_path: Path) -> bool:
    """Enrich multiple images using metadata from JSON file."""
    import json
    from ingest_schedule import EFU_FIELDNAMES
    from edit_efu_metadata import _write_efu, _load_efu
    
    print(f"\n[clipboard-watcher] BATCH ENRICH with JSON")
    print(f"  JSON: {json_path}")
    print(f"  Images: {len(image_paths)}")
    
    if not json_path.exists():
        print(f"[error] JSON file not found: {json_path}")
        _beep("error")
        return False
    
    # Load JSON metadata
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            metadata_map = json.load(f)
        print(f"  → Loaded {len(metadata_map)} entries from JSON")
    except Exception as exc:
        print(f"[error] Failed to load JSON: {exc}")
        _beep("error")
        return False
    
    if not image_paths:
        print(f"[warn] No images to enrich")
        _beep("no_match")
        return False
    
    # Group images by parent folder (one EFU per folder)
    from collections import defaultdict
    by_folder = defaultdict(list)
    for img in image_paths:
        by_folder[img.parent].append(img)
    
    _beep("start")
    total_enriched = 0
    
    for folder, images in by_folder.items():
        efu_path = folder / ".metadata.efu"
        print(f"\n  Processing folder: {folder}")
        print(f"    EFU: {efu_path}")
        
        # Load existing EFU
        if efu_path.exists():
            try:
                fieldnames, rows = _load_efu(efu_path)
                print(f"    → Loaded {len(rows)} existing entries")
            except Exception as exc:
                print(f"    ⚠ Could not read existing EFU: {exc}")
                rows = []
                fieldnames = EFU_FIELDNAMES
        else:
            rows = []
            fieldnames = EFU_FIELDNAMES
        
        # Build lookup: filename -> row_index
        row_lookup = {row.get("Filename", ""): idx for idx, row in enumerate(rows)}
        
        # Enrich each image
        for img in images:
            code = img.stem  # e.g., "PL-01"
            
            if code not in metadata_map:
                print(f"    ⚠ {img.name}: No JSON data for '{code}', skipping")
                continue
            
            json_data = metadata_map[code]
            
            # Find existing row or create new
            if img.name in row_lookup:
                row = rows[row_lookup[img.name]]
                print(f"    ✓ {img.name}: Updating existing entry")
            else:
                row = {field: "-" for field in fieldnames}
                row["Filename"] = img.name
                rows.append(row)
                print(f"    ✓ {img.name}: Creating new entry")
            
            # Map JSON fields to EFU columns
            if "subject" in json_data:
                row["custom_property_0"] = json_data["subject"]
            if "title" in json_data:
                row["custom_property_1"] = json_data["title"]
            if "brand" in json_data:
                row["custom_property_2"] = json_data["brand"]
            if "color" in json_data or "finish" in json_data:
                color = json_data.get("color", "")
                finish = json_data.get("finish", "")
                row["custom_property_4"] = f"{color} {finish}".strip() if color and finish else (color or finish or "-")
            if "location" in json_data:
                row["custom_property_5"] = json_data["location"]
            if "dimension" in json_data:
                row["custom_property_7"] = json_data["dimension"]
            if "code" in json_data:
                row["custom_property_8"] = json_data["code"]
            
            total_enriched += 1
        
        # Write EFU
        try:
            _write_efu(efu_path, fieldnames, rows)
            print(f"    ✓ EFU saved: {efu_path}")
        except Exception as exc:
            print(f"    [error] Failed to write EFU: {exc}")
            _beep("error")
            return False
    
    _beep("success")
    print(f"\n[clipboard-watcher] Done ✓ - {total_enriched} entries enriched")
    return True


def _enrich_image(file_path: Path, asset_type: str | None = None) -> bool:
    """Enrich image file with AI metadata using ingest_asset.py."""
    from ingest_asset import (
        infer_metadata_fields,
        enrich_row_with_models,
    )
    from move_delete_assets import (
        _load_efu,
        _write_efu,
        _row_basename,
    )

    print(f"  Type: Image")

    efu_path = file_path.parent / ".metadata.efu"
    fieldnames: list[str]
    rows: list[dict]
    existing_row = None
    row_index = -1

    if efu_path.exists():
        fieldnames, rows = _load_efu(efu_path)
        target_basename = file_path.name.lower()
        for i, row in enumerate(rows):
            if _row_basename(row) == target_basename:
                existing_row = row
                row_index = i
                break
    else:
        # Create new EFU with canonical headers
        fieldnames = [
            "Filename", "Rating", "Tags", "URL", "Comment", "ArchiveFile",
            "SourceMetadata", "Content Status", "CRC-32",
            "custom_property_0", "custom_property_1", "custom_property_2",
            "custom_property_3", "custom_property_4", "custom_property_5",
            "custom_property_6", "custom_property_7", "custom_property_8",
            "custom_property_9",
        ]
        rows = []
    
    # Auto-detect asset type from existing row if not provided
    if not asset_type and existing_row:
        # Extract from Subject field (custom_property_0): "Vegetation/Deciduous Tree" -> "vegetation"
        subject = existing_row.get("custom_property_0", "")
        if subject and "/" in subject:
            asset_type = subject.split("/")[0].strip().lower()
            print(f"  Asset type auto-detected from existing row: {asset_type}")
    
    # Validate asset type
    if not asset_type:
        print(f"[error] Asset type required for image enrichment")
        print(f"  Usage: \"G:\\DB\\asset.jpg\" enrich furniture")
        print(f"  Or for existing rows: \"G:\\DB\\asset.jpg\" enrich (auto-detects type)")
        _beep("error")
        return False
    
    print(f"  Asset type: {asset_type}")

    # Enrich using ingest_asset functions
    try:
        _beep("start")
        print(f"  Running AI enrichment...")
        
        # Get source stem from filename
        source_stem = file_path.stem
        
        # Run full enrichment pipeline
        metadata = infer_metadata_fields(
            asset_type,
            source_stem,
            image_path=file_path,
            sidecar_text=""
        )
        enriched_row = enrich_row_with_models(
            file_path,
            source_stem,
            asset_type,
            metadata,
            existing_row.copy() if existing_row else {}
        )
        
        # Set Filename field (critical - otherwise empty in EFU)
        enriched_row["Filename"] = file_path.name
        
        if existing_row:
            # Merge with existing (preserve manual edits)
            rows[row_index] = enriched_row
            action = "updated"
        else:
            # New entry
            rows.append(enriched_row)
            action = "created"
        
        print(f"  ✓ Row {action}: {file_path.name}")
    except Exception as exc:
        print(f"[error] AI enrichment failed: {exc}")
        _beep("error")
        return False

    # Write back to EFU
    try:
        _write_efu(efu_path, fieldnames, rows)
        print(f"  ✓ EFU saved: {efu_path}")
        _beep("success")
        return True
    except Exception as exc:
        print(f"[error] Failed to write EFU: {exc}")
        _beep("error")
        return False


def _enrich_pdf(file_path: Path, asset_type: str | None = None) -> bool:
    """Extract PDF schedule and create .metadata.efu entries using ingest_schedule.py."""
    from ingest_schedule import (
        extract_from_pdf,
        detect_root_from_name,
        cleanup_rows_with_ai,
        write_metadata_efu,
    )

    print(f"  Type: PDF Schedule")

    # Determine asset type
    if asset_type:
        root = asset_type
        print(f"  Asset type (specified): {asset_type}")
    else:
        root = detect_root_from_name(file_path.name).lower()
        print(f"  Asset type (auto-detected): {root}")

    output_dir = file_path.parent
    album = output_dir.name
    author = output_dir.parent.name if output_dir.parent else "-"

    print(f"  Album: {album}")
    print(f"  Author: {author}")

    # Extract data from PDF
    try:
        print(f"  Extracting schedule data...")
        rows, page_indices, project, client = extract_from_pdf(file_path, root)
        print(f"  → Extracted {len(rows)} rows")
        if project != "-":
            print(f"  → Project: {project}")
        if client != "-":
            print(f"  → Client: {client}")
    except Exception as exc:
        print(f"[error] PDF extraction failed: {exc}")
        _beep("error")
        return False

    if not rows:
        print("[warn] No rows extracted from PDF")
        _beep("no_match")
        return False

    # AI cleanup
    print(f"  Running AI cleanup...")
    _beep("start")
    try:
        cleaned_rows = cleanup_rows_with_ai(rows, file_path)
    except Exception as exc:
        print(f"[warn] AI cleanup skipped: {exc}")
        cleaned_rows = rows

    # Set SourceMetadata with folder context (Album is the output folder name)
    for row in cleaned_rows:
        # Album/Author context can be added to SourceMetadata if needed
        if row.get("SourceMetadata") == "-":
            row["SourceMetadata"] = f"extracted from {file_path.name} (album: {album})"

    # Write metadata EFU
    efu_path = output_dir / ".metadata.efu"
    print(f"  Writing metadata...")
    try:
        written, replaced = write_metadata_efu(cleaned_rows, efu_path)
        print(f"  ✓ {written} entries written")
        if replaced > 0:
            print(f"  ✓ {replaced} entries updated")
    except Exception as exc:
        print(f"[error] Failed to write EFU: {exc}")
        _beep("error")
        return False

    _beep("success")
    print(f"[clipboard-watcher] Done ✓")
    return True


def _handle_audit(efu_path: Path) -> bool:
    """Audit .metadata.efu file and remove entries for files no longer in the folder."""
    print(f"\n[clipboard-watcher] AUDIT {efu_path}")

    if not efu_path.exists():
        print(f"[error] EFU file not found: {efu_path}")
        _beep("error")
        return False

    if efu_path.name != ".metadata.efu":
        print(f"[error] Not a .metadata.efu file: {efu_path}")
        _beep("error")
        return False

    folder = efu_path.parent
    print(f"  Auditing folder: {folder}")

    # Read EFU file
    try:
        import csv
        with open(efu_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        print(f"  → Total entries in EFU: {len(rows)}")
    except Exception as exc:
        print(f"[error] Failed to read EFU: {exc}")
        _beep("error")
        return False

    # Check which files exist
    removed_count = 0
    kept_rows = []

    for row in rows:
        filename = (row.get("Filename") or "").strip()
        if not filename or filename == "-":
            kept_rows.append(row)
            continue

        file_path = folder / filename
        if file_path.exists():
            kept_rows.append(row)
        else:
            print(f"  → Removing entry for missing file: {filename}")
            removed_count += 1

    if removed_count == 0:
        print(f"  ✓ All entries reference existing files (no cleanup needed)")
        _beep("success")
        return True

    # Write back updated EFU
    if not DRY_RUN:
        try:
            import csv
            with open(efu_path, 'w', encoding='utf-8-sig', newline='') as f:
                if kept_rows:
                    fieldnames = list(kept_rows[0].keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(kept_rows)
                else:
                    # If no rows left, write empty EFU with headers
                    if rows:
                        fieldnames = list(rows[0].keys())
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
            print(f"  → Removed {removed_count} entries from EFU")
        except Exception as exc:
            print(f"[error] Failed to write EFU: {exc}")
            _beep("error")
            return False
    else:
        print(f"  (dry-run) Would remove {removed_count} entries")

    _beep("success")
    print(f"[clipboard-watcher] Done ✓")
    return True

def _handle_create(file_path: Path, args: list[Tuple[str, str]] | None = None) -> bool:
    """Extract images from PDF schedule and name them by code (e.g., PL-01.jpg).
    
    Images only - no metadata EFU. User will enrich later with JSON file.
    """
    from ingest_schedule import (
        extract_codes_from_pdf,
        extract_page_images,
        get_largest_image,
        _find_header_xrefs,
    )

    print(f"\n[clipboard-watcher] CREATE (extract images) from PDF {file_path}")

    if not file_path.exists() or file_path.suffix.lower() != ".pdf":
        print(f"[error] Not an existing PDF: {file_path}")
        _beep("error")
        return False

    output_dir = file_path.parent
    print(f"  Output directory: {output_dir}")

    # Extract codes and page indices
    try:
        print(f"  Extracting codes from PDF...")
        codes, page_indices, project, client = extract_codes_from_pdf(file_path)
        print(f"  → Found {len(codes)} items")
        if project != "-":
            print(f"  → Project: {project}")
        if client != "-":
            print(f"  → Client: {client}")
    except Exception as exc:
        print(f"[error] PDF extraction failed: {exc}")
        _beep("error")
        return False

    if not codes:
        print("[warn] No items with codes found")
        _beep("no_match")
        return False

    # Extract images
    print(f"  Extracting images...")
    try:
        import fitz
        with fitz.open(str(file_path)) as doc:
            header_xrefs = _find_header_xrefs(doc)
            image_count = 0
            for code, page_idx in zip(codes, page_indices):
                img_list = extract_page_images(doc, page_idx, header_xrefs)
                if img_list:
                    # Get the largest image for this page
                    largest_img = get_largest_image(img_list)
                    if largest_img:
                        # Save image with code as filename
                        img_path = output_dir / f"{code}.jpg"
                        img_path.write_bytes(largest_img)
                        print(f"  → {code}.jpg")
                        image_count += 1
        print(f"  ✓ Extracted {image_count} images")
    except Exception as exc:
        print(f"[error] Image extraction failed: {exc}")
        import traceback
        traceback.print_exc()
        _beep("error")
        return False

    _beep("success")
    print(f"[clipboard-watcher] Done ✓ - {image_count} images saved to {output_dir}")
    print(f"  Next: Generate JSON metadata and run: \"<images>\" \"<json>\" enrich:")
    return True

def _handle_set(file_path: Path, updates: List[Tuple[str, str]]) -> bool:
    """Set multiple metadata fields on an asset."""
    print(f"\n[clipboard-watcher] SET {file_path}")

    if not file_path.exists():
        print(f"[error] File not found: {file_path}")
        _beep("error")
        return False

    efu_path = file_path.parent / ".metadata.efu"
    target_basenames = {file_path.name.lower()}
    total_updated = 0

    # Validate ratings before proceeding
    for column, value in updates:
        if column == "Rating":
            try:
                val_int = int(value)
                if val_int not in VALID_RATINGS:
                    print(f"[warn] {value} is not a standard rating. Standard: {sorted(VALID_RATINGS)}")
            except ValueError:
                print(f"[error] Rating must be an integer, got: {value!r}")
                _beep("error")
                return False

    for column, value in updates:
        print(f"\n  Field: {column}  Value: {value!r}")
        updated = update_efu(efu_path, target_basenames, column, value, DRY_RUN)
        total_updated += updated

    if total_updated == 0:
        print(f"\n  [warn] No rows updated")
        _beep("no_match")
        return False

    _beep("success")
    print(f"\n[clipboard-watcher] Done ✓ - {total_updated} change(s) applied")
    return True

# ---------------------------------------------------------------------------
# Main Loop
# ---------------------------------------------------------------------------
def run():
    global _last_seen, DRY_RUN

    parser = argparse.ArgumentParser(
        description="Background clipboard watcher for RR asset management.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without modifying any files.")
    args = parser.parse_args()
    DRY_RUN = args.dry_run

    if DRY_RUN:
        print("[clipboard-watcher] DRY RUN mode enabled - no changes will be saved")

    print(f"[clipboard-watcher] Started, polling every {CHECK_INTERVAL}s (Ctrl+C to stop)")
    print("[clipboard-watcher] Copy commands like:")
    print("  Single existing:  g:/db/image.jpg enrich:   -> AI-enrich metadata (uses existing asset_type)")
    print("  Single new:       g:/db/image.jpg enrich furniture -> Create entry with specified type")
    print("  Two-step:         g:/db/image.jpg then paste description -> AI-enrich with description")
    print("  Explicit describe: \"g:/db/image.jpg\" describe \"description text here\" -> AI-enrich")
    print("  Multiple new:     \"g:/db/1.jpg\" \"g:/db/2.jpg\" enrich furniture -> Create multiple entries")
    print("  g:/db/.metadata.efu audit:   -> Audit EFU and remove entries for missing files")
    print("  g:/db/schedule.pdf create: -> Extract images + create metadata")
    print("  g:/db/image.jpg set Rating=99 Tags=lighting -> Update fields\n")

    if not HAS_SEND2TRASH:
        print("[warn] send2trash not installed - audit function available but not used for file deletion")
        print("[warn] Install with: pip install send2trash for future file operations\n")

    # Initialize _last_seen with current clipboard to ignore pre-existing content
    try:
        _last_seen = (pyperclip.paste() or "").strip()
        if _last_seen:
            preview = _last_seen[:80] + ("..." if len(_last_seen) > 80 else "")
            print(f"[clipboard-watcher] Ignoring pre-existing clipboard: {preview}")
        else:
            print(f"[clipboard-watcher] Clipboard empty at startup")
    except Exception:
        _last_seen = ""
        print(f"[clipboard-watcher] Could not read clipboard at startup")
    
    print(f"[clipboard-watcher] Monitoring clipboard... (Press Ctrl+C to stop)\n")

    while True:
        try:
            time.sleep(CHECK_INTERVAL)

            # Reload .env on every iteration to pick up any changes user made to configuration
            repo_root = Path(__file__).resolve().parents[1]
            for env_name in (".env", ".env.local"):
                env_path = repo_root / env_name
                if not env_path.exists() or not env_path.is_file:
                    continue
                try:
                    for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
                        line = raw.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key:
                            # Always update from .env - allows picking up config changes
                            # while watcher is running (model names, API keys, etc.)
                            os.environ[key] = value
                except Exception:
                    continue

            # Read clipboard
            try:
                current = (pyperclip.paste() or "").strip()
            except Exception:
                continue

            if not current or current == _last_seen:
                continue

            # Check for description-based enrichment (two-step workflow)
            if _waiting_for_description:
                # Check if we've timed out
                elapsed = time.time() - _last_paste_time
                if elapsed > _DESCRIPTION_TIMEOUT:
                    print(f"[clipboard-watcher] Timed out waiting for description")
                    _waiting_for_description = False
                    _pending_image_path = None
                    _last_seen = current
                    continue

                # Check if current text looks like a description
                if _looks_like_description(current):
                    print()
                    print(f"[clipboard-watcher] Received description for: {_pending_image_path}")
                    print(f"[clipboard-watcher] Description snippet: {current[:100]}...")
                    _beep("start")

                    # Handle enrichment with description
                    success = _handle_describe_enrich(_pending_image_path, current)

                    _waiting_for_description = False
                    _pending_image_path = None
                    _last_seen = current

                    if success:
                        print(f"[clipboard-watcher] Done ✓")
                        _beep("success")
                    else:
                        _beep("error")

                    continue

            # Check if this looks like an image file path that should trigger waiting state
            if _is_single_image_path(current):
                path = Path(current.strip('"').strip())
                if path.exists() and _is_image_file(path):
                    print(f"[clipboard-watcher] Image path detected, waiting for description (timeout: {int(_DESCRIPTION_TIMEOUT)}s)")
                    print(f"[clipboard-watcher] If not pasting a description, copy anything else to cancel")
                    _waiting_for_description = True
                    _pending_image_path = path
                    _last_paste_time = time.time()
                    _last_seen = current
                    _beep("start")
                    continue

            # Check if this looks like a command for us
            if not _looks_like_command(current):
                _last_seen = current
                continue

            # Parse command
            parsed = parse_command(current)
            if parsed is None:
                print(f"[clipboard-watcher] Could not parse command: {current[:80]}")
                _last_seen = current
                continue
            file_path, action, args = parsed

            if file_path is None or action is None:
                print(f"[clipboard-watcher] Invalid command (no path or action found): {current[:80]}")
                _last_seen = current
                continue

            print()
            print(f"[clipboard-watcher] Received: {current}")
            _beep("start")

            # Dispatch (file_paths is always a list now)
            success = True
            file_count = len(file_path)
            success_count = 0

            if action == "describe":
                for fp in file_path:
                    description = next(arg[1] for arg in args if arg[0] == "description") if args else ""
                    if not description:
                        print(f"[error] No description provided for 'describe' command")
                        _beep("error")
                        continue
                    if _handle_describe_enrich(fp, description):
                        success_count += 1
                    else:
                        success = False
            elif action == "enrich":
                # Enrich handles batching internally (supports JSON)
                if _handle_enrich(file_path, args):
                    success_count = file_count
                else:
                    success = False
            elif action == "audit":
                for fp in file_path:
                    if _handle_audit(fp):
                        success_count += 1
                    else:
                        success = False
            elif action == "create":
                for fp in file_path:
                    if _handle_create(fp):
                        success_count += 1
                    else:
                        success = False
            elif action == "set":
                if args is None:
                    print("[error] Invalid 'set' command syntax")
                    _beep("error")
                    success = False
                else:
                    for fp in file_path:
                        if _handle_set(fp, args):
                            success_count += 1
                        else:
                            success = False
            else:
                print(f"[error] Unknown action: {action}")
                _beep("error")
                success = False

            # Summary
            if file_count > 1:
                print(f"\n[clipboard-watcher] Summary: {success_count}/{file_count} files completed successfully")

            # Done beep
            if success:
                _beep("success")
            else:
                _beep("error")

            # Update last_seen so we don't reprocess
            _last_seen = current

        except KeyboardInterrupt:
            print("\n[clipboard-watcher] Stopped.")
            break
        except Exception as exc:
            # Never let an unhandled exception kill the background loop
            print(f"[clipboard-watcher] Unhandled error (continuing): {exc}")
            _beep("error")
            continue

if __name__ == "__main__":
    run()
