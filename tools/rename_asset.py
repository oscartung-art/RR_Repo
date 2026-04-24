#!/usr/bin/env python3
"""
rename_asset.py — Handles file renaming for assets (images + archives) based on metadata.
Extracts renaming logic from original ingest_asset.py.
"""

import os
import re
import zlib
import shutil
import concurrent.futures
import time
from pathlib import Path


def compute_crc32(file_path: Path) -> str:
    """Compute CRC-32 checksum of a file."""
    checksum = 0
    with file_path.open("rb") as file_handle:
        while chunk := file_handle.read(1024 * 1024):
            checksum = zlib.crc32(chunk, checksum)
    return f"{checksum & 0xFFFFFFFF:08X}"


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


def build_short_base_name(asset_type: str, row: dict[str, str], hints: dict[str, str], fallback: str) -> str:
    """Build short base filename from asset type, metadata row, and hints."""
    # New schema: Subject is in custom_property_0
    subject_value = subject_path_leaf(row.get("custom_property_0", "")) or row.get("custom_property_0", "")
    if asset_type == "furniture":
        # Title is in custom_property_1
        model_name_token = sanitize_name_token(row.get("custom_property_1", "") or "")
        preferred = [subject_value, model_name_token] if model_name_token and model_name_token != "-" else [subject_value]
    elif asset_type == "fixture":
        # Title is in custom_property_1
        model_name_token = sanitize_name_token(row.get("custom_property_1", "") or "")
        preferred = [p for p in [subject_value, model_name_token] if p and p != "-"]
    elif asset_type == "vegetation":
        # Author is in custom_property_4
        preferred = [subject_value, row.get("custom_property_4", "")]
    elif asset_type == "people":
        # Author is in custom_property_4
        preferred = [subject_value, row.get("custom_property_4", "")]
    elif asset_type == "material":
        # Company is in custom_property_2
        preferred = [subject_value, row.get("custom_property_2", "")]
    elif asset_type == "buildings":
        # Company is in custom_property_2
        preferred = [subject_value, row.get("custom_property_2", "")]
    else:
        preferred = [subject_value, row.get("custom_property_5", "")]

    tokens = [sanitize_name_token(x) for x in preferred if x]
    tokens = [t for t in tokens if t]
    deterministic = "_".join(tokens) if tokens else (sanitize_name_token(fallback) or "Asset")

    if asset_type in ("furniture", "fixture"):
        return deterministic

    try:
        qwen_name = clean_name_with_qwen(
            asset_type=asset_type,
            source_stem=fallback,
            mapped_subject=row.get("custom_property_0", ""),
            mapped_brand=row.get("custom_property_2", ""),
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
    """Ensure image and archive target paths are unique in their directories."""
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
    """Move image and archive pair to new locations with new base name."""
    if image_target is None or archive_target is None:
        image_target, archive_target, _ = ensure_unique_targets(
            new_base_name,
            image_path.suffix.lower(),
            archive_path.suffix.lower(),
            image_dir=image_dir,
            archive_dir=archive_dir,
        )
    if overwrite:
        if image_target.resolve() != image_path.resolve() and image_target.exists():
            image_target.unlink()
        if archive_target.resolve() != archive_path.resolve() and archive_target.exists():
            archive_target.unlink()
    if image_path.resolve() != image_target.resolve():
        moved_image = _move_with_timeout(str(image_path), str(image_target))
    else:
        moved_image = image_target
    if archive_path.resolve() != archive_target.resolve():
        moved_archive = _move_with_timeout(str(archive_path), str(archive_target))
    else:
        moved_archive = archive_target
    return moved_image, moved_archive


def subject_path_leaf(value: str) -> str:
    """Return the terminal segment from a Subject path."""
    if not value or value == "-":
        return ""
    return value.strip().strip("/").split("/")[-1]


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


def sanitize_name_token(value: str) -> str:
    """Sanitize text for use as filename token."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", value).strip()
    if not cleaned:
        return ""
    return "".join(part[:1].upper() + part[1:] for part in cleaned.split())


def clean_name_with_qwen(asset_type: str, source_stem: str, mapped_subject: str, mapped_brand: str) -> str:
    """Clean filename using Qwen LLM (implementation from ingest_asset.py)."""
    raise NotImplementedError("This function needs to be implemented from ingest_asset.py")


# Constants (from ingest_asset.py)
THUMBNAIL_BASE = Path(r"G:\DB")
ARCHIVE_BASE = Path(r"G:\DB")
MOVE_FILES = False

# Configurable path overrides — set via env vars or CLI flags to remap drives.
_THUMBNAIL_BASE_ENV = os.environ.get("INGEST_THUMBNAIL_BASE", "")
_ARCHIVE_BASE_ENV = os.environ.get("INGEST_ARCHIVE_BASE", "")
if _THUMBNAIL_BASE_ENV:
    THUMBNAIL_BASE = Path(_THUMBNAIL_BASE_ENV)
if _ARCHIVE_BASE_ENV:
    ARCHIVE_BASE = Path(_ARCHIVE_BASE_ENV)

# Legacy move behavior is now opt-in only.
_MOVE_FILES_ENV = os.environ.get("INGEST_MOVE_FILES", "0").strip().lower()
MOVE_FILES = _MOVE_FILES_ENV in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Rename asset files based on metadata")
    parser.add_argument("image_path", help="Path to image file")
    parser.add_argument("archive_path", nargs="?", help="Path to archive file (optional)")
    parser.add_argument("--asset-type", required=True, help="Asset type (furniture, fixture, etc.)")
    parser.add_argument("--metadata", help="Path to metadata file (JSON or EFU)")
    args = parser.parse_args()

    image_path = Path(args.image_path)
    archive_path = Path(args.archive_path) if args.archive_path else None

    print(f"Processing: {image_path}")
    if archive_path:
        print(f"Archive: {archive_path}")

    # TODO: Implement main logic
    print("Main functionality not yet implemented. This is a skeleton file.")
