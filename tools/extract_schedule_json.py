#!/usr/bin/env python3
"""Extract metadata from design schedule PDF, generate JSON, and extract relevant images.

This script combines pattern analysis, JSON extraction, and image extraction:
  1. Analyzes PDF structure and detects patterns
  2. Extracts metadata to JSON keyed by code
  3. Extracts relevant product images (skips headers, icons, logos)
  4. Names images by code for easy matching

Usage:
    # Preview extraction only
    python extract_schedule_json.py --dry-run "schedule.pdf"

    # Write JSON file only
    python extract_schedule_json.py --yes "schedule.pdf"

    # Write JSON + extract images
    python extract_schedule_json.py --yes --extract-images "schedule.pdf"

Output:
    Writes <PDF_BASENAME>.json in same directory as PDF.
    Optionally extracts <CODE>.jpg files to same directory.
"""

# Fix output encoding issues on Windows
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from pathlib import Path
import json
import argparse

# Add tools directory to Python path for imports
import os
script_dir = Path(__file__).resolve().parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

# Import extraction logic from ingest_schedule.py
try:
    from ingest_schedule import (
        extract_from_pdf,
        detect_root_from_name,
        cleanup_rows_with_ai,
        EFU_FIELDNAMES,
        extract_page_images,
        _find_header_xrefs,
        get_largest_image,
        combine_images
    )
except ImportError as e:
    print(f"Error: Could not import from ingest_schedule.py: {e}", file=sys.stderr)
    print("Make sure this script is in the tools/ directory", file=sys.stderr)
    sys.exit(1)

# Try to import fitz (pymupdf) for image extraction
try:
    import fitz
except ImportError:
    fitz = None


def extract_metadata_to_json(pdf_path: Path, root: str) -> tuple[dict[str, dict], str, str, list[dict]]:
    """Extract metadata from PDF and return as JSON keyed by code.

    Returns:
        (metadata_dict, project, client, rows_with_page_indices)

        where metadata_dict is:
        {
            "PL-01": {
                "subject": "Material/NaturalStone",
                "title": "Carrara Marble",
                "brand": "Italian Marble Co",
                "color": "White Polished",
                "location": "Living Room Floor",
                "dimension": "600x600x20mm",
                "code": "PL-01"
            },
            ...
        }

        and rows_with_page_indices is list of (row, page_index)
    """
    rows, page_indices, project, client = extract_from_pdf(pdf_path, root)

    # Clean up with AI
    print(f"  Extracted {len(rows)} entries, running AI cleanup...")
    rows = cleanup_rows_with_ai(rows, pdf_path)

    # If no rows found, attempt a general fallback: ask AI to infer structure from full page text.
    if not rows:
        print("  No structured rows extracted - running general AI structure inference fallback...")
        try:
            import pdfplumber
            from ingest_schedule import extract_code_and_item_type

            synthetic_rows = []
            new_page_indices = []
            with pdfplumber.open(str(pdf_path)) as pdf:
                for page_index, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    if not text.strip():
                        continue
                    code, item_type = extract_code_and_item_type(text)
                    if code == "-":
                        code = f"PAGE-{page_index+1:02d}"
                    # Use first line or first 80 chars as brief title
                    first_line = (text.strip().splitlines()[0] or "")[:80]
                    synthetic_rows.append({
                        "Filename": f"{code}.jpg",
                        "Rating": "-",
                        "Tags": "-",
                        "URL": "-",
                        "Comment": "-",
                        "ArchiveFile": "-",
                        "SourceMetadata": f"extracted page text: {pdf_path.name} page {page_index+1}",
                        "Content Status": "Draft",
                        "CRC-32": "-",
                        "custom_property_0": item_type if item_type and item_type != "-" else "-",
                        "custom_property_1": first_line or "-",
                        "custom_property_2": "-",
                        "custom_property_3": "-",
                        "custom_property_4": "-",
                        "custom_property_5": "-",
                        "custom_property_6": "-",
                        "custom_property_7": "-",
                        "custom_property_8": code,
                        "custom_property_9": "-",
                    })
                    new_page_indices.append(page_index)
            if synthetic_rows:
                print(f"  → Created {len(synthetic_rows)} synthetic rows for AI inference")
                # Let AI attempt to clean/structure these synthetic rows using existing cleanup helper
                rows = cleanup_rows_with_ai(synthetic_rows, pdf_path)
                page_indices = new_page_indices
        except Exception as e:
            print(f"  Fallback inference failed: {e}")

    # Build JSON dict
    result = {}
    rows_with_pages = []
    for row, page_idx in zip(rows, page_indices):
        code = row.get("custom_property_8", "-")
        if code == "-":
            continue

        # Map EFU columns to JSON keys
        result[code] = {
            "subject": row.get("custom_property_0", "-"),
            "title": row.get("custom_property_1", "-"),
            "brand": row.get("custom_property_2", "-"),
            "color": row.get("custom_property_4", "-"),
            "location": row.get("custom_property_5", "-"),
            "dimension": row.get("custom_property_7", "-"),
            "code": code
        }
        rows_with_pages.append((row, page_idx, code))

    return result, project, client, rows_with_pages


def extract_images_from_pdf(pdf_path: Path, rows_with_pages: list[tuple[dict, int, str]]) -> int:
    """Extract relevant images from PDF and save as <CODE>.jpg.

    Skips:
    - Header images (recurring on >50% of pages)
    - Small icons/thin lines (<60px)
    - Useless content

    Returns number of images extracted.
    """
    if not fitz:
        print("  ⚠ Image extraction skipped: pymupdf (fitz) not installed")
        return 0

    doc = fitz.open(str(pdf_path))
    header_xrefs = _find_header_xrefs(doc)
    output_dir = pdf_path.parent
    extracted_count = 0
    skipped_count = 0

    print(f"  Analyzing {doc.page_count} pages for product images...")
    print(f"  → Found {len(header_xrefs)} header/logo images to skip")

    for row, page_idx, code in rows_with_pages:
        if page_idx < 0 or page_idx >= doc.page_count:
            print(f"  ⚠ Invalid page index {page_idx} for code {code}")
            continue

        # Get images from this page
        image_list = extract_page_images(doc, page_idx, header_xrefs)

        if not image_list:
            skipped_count += 1
            continue

        # Process images: if multiple, combine side-by-side
        if len(image_list) == 1:
            # Just take the largest (and only) image
            img_data = get_largest_image(image_list)
        else:
            # Extract all valid image bytes and combine
            img_bytes = [img[0] for img in image_list]
            img_data = combine_images(img_bytes)

        # Save as <CODE>.jpg
        output_path = output_dir / f"{code}.jpg"
        with open(output_path, "wb") as f:
            f.write(img_data)

        extracted_count += 1
        print(f"  → Extracted: {output_path.name}")

    doc.close()

    if extracted_count > 0:
        print(f"  ✓ Extracted {extracted_count} product images")
    if skipped_count > 0:
        print(f"  ℹ Skipped {skipped_count} pages with no relevant images")

    return extracted_count


def format_preview_table(metadata: dict[str, dict], project: str, client: str,
                         has_image_support: bool) -> str:
    """Format extracted metadata as readable table."""
    lines = []
    lines.append(f"\n{'='*80}")
    lines.append(f"Project: {project}")
    lines.append(f"Client: {client}")
    lines.append(f"Total entries: {len(metadata)}")
    lines.append(f"Image extraction supported: {'Yes' if has_image_support else 'No (install pymupdf)'}")
    lines.append(f"{'='*80}\n")

    # Table header
    lines.append(f"{'Code':<12} {'Subject':<25} {'Title':<30} {'Brand':<20}")
    lines.append(f"{'-'*12} {'-'*25} {'-'*30} {'-'*20}")

    # Table rows
    for code in sorted(metadata.keys()):
        entry = metadata[code]
        subject = entry.get("subject", "-")[:24]
        title = entry.get("title", "-")[:29]
        brand = entry.get("brand", "-")[:19]
        lines.append(f"{code:<12} {subject:<25} {title:<30} {brand:<20}")

    lines.append("")

    # Show first entry in detail
    if metadata:
        first_code = sorted(metadata.keys())[0]
        first_entry = metadata[first_code]
        lines.append("\nFirst entry (full detail):")
        lines.append(json.dumps({first_code: first_entry}, indent=2))

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Extract schedule metadata to JSON, and optionally extract images"
    )
    parser.add_argument("pdf_path", help="Path to schedule PDF file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview extraction without writing JSON or extracting images"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Write JSON file (required to actually write)"
    )
    parser.add_argument(
        "--extract-images",
        action="store_true",
        help="Extract product images from PDF (skips headers, icons, logos)"
    )
    parser.add_argument(
        "--asset-type",
        help="Override asset type detection (material, fixture, furniture, etc.)"
    )

    args = parser.parse_args()

    # Validate input
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    if not pdf_path.suffix.lower() == ".pdf":
        print(f"Error: Not a PDF file: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    # Check for image extraction support
    has_image_support = fitz is not None
    if args.extract_images and not has_image_support:
        print("Error: Image extraction requires pymupdf (fitz) — install with pip install pymupdf", file=sys.stderr)
        sys.exit(1)

    # Determine asset type root
    if args.asset_type:
        root = args.asset_type.capitalize()
    else:
        root = detect_root_from_name(pdf_path.name)

    print(f"[extract-schedule-json] Processing: {pdf_path.name}")
    print(f"  Asset type: {root}")
    print(f"  Mode: {'Preview' if args.dry_run else 'Extract'}")
    if args.extract_images and not args.dry_run:
        print(f"  Extracting images: Yes")

    # Extract metadata
    try:
        metadata, project, client, rows_with_pages = extract_metadata_to_json(pdf_path, root)
    except Exception as e:
        print(f"Error during extraction: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    if not metadata:
        print("Error: No entries extracted from PDF", file=sys.stderr)
        sys.exit(1)

    # Show preview
    preview = format_preview_table(metadata, project, client, has_image_support)
    print(preview)

    # Dry run - stop here
    if args.dry_run:
        print("\n[DRY RUN] No files written")
        print(f"Would write: {pdf_path.stem}.json")
        if args.extract_images:
            print(f"Would extract images: {len(metadata)} entries (one image per page with code)")
        return

    # Write JSON file and optionally extract images
    if args.yes:
        # Write JSON
        output_path = pdf_path.parent / f"{pdf_path.stem}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print(f"\n✓ JSON written: {output_path}")
        print(f"  {len(metadata)} entries")

        # Extract images if requested
        img_count = 0
        if args.extract_images:
            print(f"\n[extract-schedule-json] Extracting product images...")
            img_count = extract_images_from_pdf(pdf_path, rows_with_pages)

        # Print next steps
        print("\nNext steps:")
        print("  1. Review/edit JSON file if needed")
        if not args.extract_images:
            print("  2. Extract images from PDF using create: command, or use --extract-images flag")
        else:
            print("  2. Images already extracted to same folder, ready to enrich")
        print("  3. Enrich images with: \"folder\" \"metadata.json\" enrich:")
    else:
        print("\n[INFO] Use --yes to write JSON file, or --dry-run to preview")
        print("\n[INFO] Use --yes --extract-images to write JSON and extract product images")


if __name__ == "__main__":
    main()