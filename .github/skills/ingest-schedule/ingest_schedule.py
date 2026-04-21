"""
ingest_schedule.py

Extracts any interior design schedule (material, sanitary, furniture, lighting, etc.)
from a PDF and writes a .metadata.efu file using canonical EFU column names.
Also extracts product images per entry and saves them as <Filename>.jpg.

Usage:
    python ingest_schedule.py "<PDF_PATH>" [--out "<OUTPUT_DIR>"] [--dry-run] [--no-images]

Output directory is prompted when --out is not provided.
If the output .metadata.efu already exists, existing rows are deduplicated by Filename.

Parsing strategy: uses page.extract_text() (reading order) so it handles
all table layout variants (2-col, 4-col, 7-col) without cell alignment issues.

EFU column mapping:
  Filename          ← <SubjectLeaf>_<Brand><ModelRef>  (synthetic identifier)
  custom_property_6 ← Code  (schedule reference code, e.g. C-SF-01, AL-01)
  Subject           ← AssetType/TitleCaseItem  (e.g. Fixture/SensorBasinMixer)
  Title             ← Model spec (without brand prefix)
  custom_property_7 ← Finish  (surface finish/treatment)
  custom_property_0 ← Colour/Color
  custom_property_5 ← Dimension  (Size)
  custom_property_1 ← Location  (room/area)
  Author            ← Parent folder name (mirrors ingest_asset.py convention)
  Album             ← Output folder name
  Company           ← Brand  (extracted from quoted model prefix)
"""

import argparse
import csv
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber is not installed. Run: pip install pdfplumber")
    sys.exit(1)

try:
    import fitz  # pymupdf
except ImportError:
    fitz = None

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None

try:
    import requests
except ImportError:
    requests = None

EFU_FIELDNAMES = [
    "Filename",
    "custom_property_6",
    "Subject",
    "Title",
    "custom_property_7",
    "custom_property_0",
    "custom_property_5",
    "custom_property_1",
    "Author",
    "Album",
    "Company",
]

# Maps keywords found in PDF filename/title to ingest_asset.py asset_type root.
_FILENAME_ROOT_KEYWORDS: list[tuple[list[str], str]] = [
    (["sanitary", "plumbing", "fitting", "wc", "bathroom"],  "Fixture"),
    (["lighting", "light", "lamp", "luminaire"],             "Fixture"),
    (["furniture", "ff&e", "ffe", "seating", "table"],       "Furniture"),
    (["material", "tile", "stone", "floor", "wall", "finish", "cladding"], "Material"),
    (["door", "window", "ironmongery", "hardware"],          "Object"),
]

OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "qwen/qwen2.5-vl-72b-instruct")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
AI_ALLOWED_UPDATE_FIELDS = {
    "Subject",
    "Title",
    "custom_property_7",
    "custom_property_0",
    "custom_property_5",
    "custom_property_1",
    "Company",
}


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Extract first valid JSON object from raw model text."""
    if not text:
        return None

    candidates: list[str] = []
    stripped = text.strip()
    candidates.append(stripped)

    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fence_match:
        candidates.append(fence_match.group(1).strip())

    start = text.find("{")
    while start >= 0:
        depth = 0
        in_string = False
        escape = False
        for i, ch in enumerate(text[start:], start=start):
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[start:i + 1])
                    break
        start = text.find("{", start + 1)

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    return None


def _normalize_ai_corrections(payload: dict[str, Any], row_count: int) -> dict[int, dict[str, str]]:
    """Validate and normalize AI corrections payload."""
    raw_corrections = payload.get("corrections")
    if not isinstance(raw_corrections, dict):
        return {}

    normalized: dict[int, dict[str, str]] = {}
    for raw_idx, raw_fixes in raw_corrections.items():
        try:
            idx = int(str(raw_idx).strip())
        except (TypeError, ValueError):
            continue
        if idx < 0 or idx >= row_count or not isinstance(raw_fixes, dict):
            continue

        valid_fixes: dict[str, str] = {}
        for key, value in raw_fixes.items():
            if key not in AI_ALLOWED_UPDATE_FIELDS:
                continue
            if value is None:
                continue
            cleaned = str(value).strip()
            if not cleaned:
                continue
            valid_fixes[key] = cleaned
        if valid_fixes:
            normalized[idx] = valid_fixes
    return normalized


def cleanup_rows_with_ai(rows: list[dict], pdf_path: Path) -> list[dict]:
    """Use Qwen VL via OpenRouter to validate and clean extracted rows."""
    if not OPENROUTER_API_KEY or requests is None:
        print("⚠ AI cleanup skipped (OpenRouter API key or requests not available)", file=sys.stderr)
        return rows
    
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            if len(pdf.pages) < 2:
                return rows
            
            sample_page = pdf.pages[1]
            page_image = sample_page.to_image(resolution=150).original
            
            import base64
            import io
            buf = io.BytesIO()
            page_image.save(buf, format='PNG')
            b64_image = base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"⚠ Could not extract page image: {e}", file=sys.stderr)
        return rows
    
    rows_csv = "\n".join([
        ",".join(EFU_FIELDNAMES),
        *[",".join([str(row.get(k, "-")) for k in EFU_FIELDNAMES]) for row in rows[:5]]
    ])
    
    prompt = f"""You are a data validation expert for interior design schedules.
Look at this sample PDF page and the extracted schedule data below.
Your task is to identify and fix ALL extraction errors systematically.

EXTRACTED DATA (first 5 rows):
{rows_csv}

CRITICAL RULES (apply ALL of them):
1. Subject: Remove redundancy (Fixture/WaterClosetCistern → Fixture/WaterCloset)
2. Color field: MUST be ONLY color name (e.g. "Black", "White", "#726 Warm Bronze")
   - REMOVE any residual email, phone, "E:", "T:", "Dimension:" text
   - If Color looks like junk/noise, set to "-"
3. Location field: MUST be ONLY room/area name (e.g. "Clubhouse female restroom")
   - REMOVE any dimensions, drawing references, or residual text
4. Size/Dimension: MUST be ONLY size spec (e.g. "467x305x155mm", "Refer to drawings")
   - REMOVE contact info
5. Replace "-" with appropriate contextual value only if visually obvious from PDF
6. Title: Keep model spec without brand prefix
7. Keep Brand/Company exactly as extracted from quoted prefix

IMPORTANT: Be AGGRESSIVE about stripping contact info - look carefully for residual emails, phone patterns, abbreviations like "E: brianli@..."

Return ONLY valid JSON:
{{
  "corrections": {{
    "0": {{"custom_property_0": "clean_color_only"}},
    "1": {{"custom_property_1": "clean_location_only"}},
    ...
  }},
  "notes": "what was fixed"
}}"""

    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image", "image": f"data:image/png;base64,{b64_image}"}
                ]
            }
        ],
        "max_tokens": 1024
    }
    
    try:
        resp = requests.post(OPENROUTER_ENDPOINT, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        if "choices" not in result or not result["choices"]:
            return rows

        content = result["choices"][0].get("message", {}).get("content", "")
        if isinstance(content, list):
            content = "\n".join(
                str(part.get("text", "")).strip()
                for part in content
                if isinstance(part, dict)
            )
        elif not isinstance(content, str):
            content = str(content)

        parsed = _extract_json_object(content)
        if parsed is None:
            print("⚠ AI cleanup returned non-JSON response; keeping extracted rows", file=sys.stderr)
            return rows

        normalized = _normalize_ai_corrections(parsed, len(rows))
        if not normalized:
            print("✓ AI cleanup: validated (no applicable corrections)", file=sys.stderr)
            return rows

        for idx, fixes in normalized.items():
            rows[idx].update(fixes)
        print(f"✓ AI cleanup: {parsed.get('notes', 'validated')}", file=sys.stderr)
             
    except Exception as e:
        print(f"⚠ AI cleanup failed: {e}", file=sys.stderr)
    
    return rows


def detect_root_from_name(name: str) -> str:
    """Infer ingest_asset.py root category from PDF filename or title."""
    n = name.lower()
    for keywords, root in _FILENAME_ROOT_KEYWORDS:
        if any(k in n for k in keywords):
            return root
    return "Asset"


def build_subject(root: str, item_detail: str, item_type: str) -> str:
    """Build Subject as Root/TitleCaseLeaf matching ingest_asset.py convention."""
    detail = item_detail if item_detail and item_detail != "-" else item_type
    leaf = sanitize_name_token(detail.lower())  # lowercase first so TitleCase applies correctly
    return f"{root}/{leaf}" if leaf else root

# Stop at next field boundary: newline + word of 3-25 chars + colon.
# Minimum 3 chars prevents matching T:, F:, E: (supplier contact labels).
_NEXT_KEY = r"(?=\n[A-Za-z][A-Za-z\s]{2,25}:|\Z)"


def extract_field(text: str, key: str) -> str:
    """Extract a field value including continuation lines, stop at next field boundary."""
    if not text:
        return "-"
    m = re.search(rf"{re.escape(key)}:\s*(.+?){_NEXT_KEY}", text, re.IGNORECASE | re.DOTALL)
    if not m:
        return "-"
    return " ".join(m.group(1).split()) or "-"


def extract_field_line(text: str, key: str) -> str:
    """Extract a field value — first line only (avoids supplier info interleaving)."""
    if not text:
        return "-"
    m = re.search(rf"{re.escape(key)}:\s*(.+?)(?=\n|\Z)", text, re.IGNORECASE)
    return m.group(1).strip() if m else "-"


def extract_code_and_item_type(text: str) -> tuple[str, str]:
    """Extract code and short item type from the '<ITEM TYPE> CODE: X' line."""
    m = re.search(r"(?:^|\n)([A-Z][A-Z\s&/]+?)\s+CODE:\s*([A-Z0-9\-]+)", text)
    if m:
        return m.group(2).strip(), m.group(1).strip()
    return "-", "-"


def sanitize_name_token(value: str) -> str:
    """Mirror of ingest_asset.py: strip non-alnum, TitleCase each word."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", value).strip()
    if not cleaned:
        return ""
    return "".join(part[:1].upper() + part[1:] for part in cleaned.split())


def strip_contact_info(value: str) -> str:
    """Remove email addresses, phone numbers, and contact patterns from a field."""
    if not value or value == "-":
        return value
    
    # Remove email addresses
    value = re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}', '', value)
    # Remove phone numbers (various formats)
    value = re.sub(r'(?:\+\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{2,4}', '', value)
    # Remove contact labels and what follows them: "E:", "T:", "F:" + email or other junk
    value = re.sub(r'\s+[ETF]:\s*[^\n]*', '', value)
    # Remove "Dimension:" labels and references
    value = re.sub(r'\s*(?:Dimension:|refer to drawings|referto drawings).*?$', '', value, flags=re.IGNORECASE)
    # Clean up extra spaces
    value = re.sub(r'\s+', ' ', value).strip()
    # Remove trailing " - " or trailing single dash
    value = re.sub(r'\s*-\s*$', '', value).strip()
    
    return value if value else "-"


def extract_brand_and_model(raw: str) -> tuple[str, str]:
    """Split '"BRAND" model-spec' into (brand, model_ref).

    Handles straight quotes and curly/smart quotes from PDFs.
    Returns ('-', raw) if no quoted brand found.
    """
    # Match opening quote (straight " or curly \u201c), brand name, closing quote
    m = re.match(r'^[\u201c\u201d"«»]([^\u201c\u201d"«»]+)[\u201c\u201d"«»]\s*(.*)', raw.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip() or "-"
    return "-", raw.strip() or "-"


def subject_leaf(subject: str) -> str:
    """Return last path segment: 'Material/Tile' → 'Tile'."""
    return subject.rstrip("/").rsplit("/", 1)[-1] if subject and subject != "-" else subject


def build_filename(subject: str, brand: str, model_ref: str) -> str:
    """Build Filename as <SubjectLeaf>_<Brand><ModelRef>.jpg matching ingest_asset.py convention."""
    leaf = sanitize_name_token(subject_leaf(subject))
    brand_tok = sanitize_name_token(brand) if brand and brand != "-" else ""
    model_tok = sanitize_name_token(" ".join(model_ref.split()[:2])) if model_ref and model_ref != "-" else ""
    suffix = brand_tok + model_tok if brand_tok else model_tok
    parts = [p for p in [leaf, suffix] if p]
    stem = "_".join(parts) if parts else "Schedule"
    return stem + ".jpg"


# ---------------------------------------------------------------------------
# Image extraction
# ---------------------------------------------------------------------------

_MIN_IMG_SIDE = 60      # px — skip icons, dividers, thin lines
_THUMB_HEIGHT = 400     # px — uniform height when combining side-by-side


def _find_header_xrefs(doc: "fitz.Document") -> set[int]:
    """Return xrefs that appear on more than half the content pages (recurring = header/logo)."""
    from collections import Counter
    counts: Counter = Counter()
    content_pages = list(doc.pages())[1:]  # skip cover
    for page in content_pages:
        for img in page.get_images(full=True):
            counts[img[0]] += 1
    threshold = max(1, len(content_pages) // 2)
    return {xref for xref, n in counts.items() if n > threshold}


def extract_page_images(doc: "fitz.Document", page_index: int, header_xrefs: set[int]) -> list[bytes]:
    """Return list of raw JPEG bytes for product images on a page (header excluded)."""
    page = doc[page_index]
    result = []
    for img in page.get_images(full=True):
        xref, _, w, h = img[0], img[1], img[2], img[3]
        if xref in header_xrefs:
            continue
        if min(w, h) < _MIN_IMG_SIDE:
            continue
        try:
            raw = doc.extract_image(xref)
            result.append(raw["image"])
        except Exception:
            continue
    return result


def combine_images(image_bytes_list: list[bytes], target_height: int = _THUMB_HEIGHT) -> bytes:
    """Combine multiple images side-by-side at uniform height; return JPEG bytes."""
    if PILImage is None:
        return image_bytes_list[0] if image_bytes_list else b""

    pil_imgs = []
    for raw in image_bytes_list:
        try:
            img = PILImage.open(io.BytesIO(raw)).convert("RGB")
            ratio = target_height / img.height
            img = img.resize((max(1, int(img.width * ratio)), target_height), PILImage.LANCZOS)
            pil_imgs.append(img)
        except Exception:
            continue

    if not pil_imgs:
        return b""

    total_w = sum(i.width for i in pil_imgs) + max(0, len(pil_imgs) - 1) * 8  # 8px gap
    canvas = PILImage.new("RGB", (total_w, target_height), (255, 255, 255))
    x = 0
    for img in pil_imgs:
        canvas.paste(img, (x, 0))
        x += img.width + 8

    buf = io.BytesIO()
    canvas.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def extract_from_pdf(pdf_path: Path, root: str) -> tuple[list[dict], list[int], str, str]:
    """Return (rows, page_indices, project, client).

    page_indices[i] is the 0-based PDF page index for rows[i].
    """
    rows = []
    page_indices = []
    project = "-"
    client = "-"
    author = pdf_path.parent.name  # mirror ingest_asset.py: use parent folder name

    with pdfplumber.open(str(pdf_path)) as pdf:
        for pdf_page_index in range(1, len(pdf.pages)):  # skip title/cover page
            page = pdf.pages[pdf_page_index]
            text = page.extract_text() or ""
            if not text.strip():
                continue

            # Parse project/client from the header (only needed once, for display only)
            if project == "-":
                project = extract_field(text, "Project")
                client = extract_field(text, "Client")

            code, item_type = extract_code_and_item_type(text)
            if code == "-":
                continue

            # Use 'Item:' field for Subject if present, else fall back to item_type
            item_detail = extract_field_line(text, "Item")
            subject = build_subject(root, item_detail, item_type)

            # Model: single-line to avoid interleaving with supplier contact columns
            raw_model = extract_field_line(text, "Model")
            brand, model_ref = extract_brand_and_model(raw_model)

            colour = extract_field(text, "Colour")
            if colour == "-":
                colour = extract_field(text, "Color")
            colour = strip_contact_info(colour)

            rows.append({
                "Filename":          build_filename(subject, brand, model_ref),
                "custom_property_6": code,
                "Subject":           subject,
                "Title":             model_ref,
                "custom_property_7": extract_field(text, "Finish"),
                "custom_property_0": colour,
                "custom_property_5": strip_contact_info(extract_field(text, "Dimension")),
                "custom_property_1": strip_contact_info(extract_field(text, "Location")),
                "Author":            author,
                "Album":             "-",
                "Company":           brand,
            })
            page_indices.append(pdf_page_index)  # 0-based index in the fitz doc

    return rows, page_indices, project, client


def write_metadata_efu(rows: list[dict], out_path: Path) -> tuple[int, int]:
    """Merge new rows into .metadata.efu, deduplicating by Filename.

    Existing rows with the same Filename are overwritten by the new data.
    Returns (written_count, replaced_count).
    """
    existing: dict[str, dict] = {}
    if out_path.exists():
        with open(out_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row.get("Filename", "").strip()
                if key:
                    existing[key] = row

    replaced = sum(1 for r in rows if r["Filename"] in existing)
    for r in rows:
        existing[r["Filename"]] = r  # overwrite if duplicate

    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=EFU_FIELDNAMES, quoting=csv.QUOTE_ALL, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(existing.values())

    return len(rows), replaced


def _album_from_out_dir(out_dir: Path) -> str:
    """Album mirrors output folder name."""
    if out_dir.name:
        return out_dir.name
    if out_dir.drive:
        return out_dir.drive
    return out_dir.anchor.rstrip("\\/") or "-"


def resolve_output_dir(pdf_path: Path, out_arg: str | None) -> Path:
    """Resolve output directory, prompting user when --out is missing."""
    if out_arg:
        out_dir = Path(out_arg).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    if not sys.stdin.isatty():
        print("ERROR: --out is required in non-interactive mode.", file=sys.stderr)
        sys.exit(1)

    while True:
        user_input = input("Output folder for .metadata.efu: ").strip().strip('"')
        if not user_input:
            print("Please provide an output folder path.")
            continue
        out_dir = Path(user_input).expanduser()
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            return out_dir
        except OSError as exc:
            print(f"Invalid output folder: {exc}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract any design schedule (material/sanitary/furniture/lighting/etc.) from PDF to .metadata.efu"
    )
    parser.add_argument("pdf", help="Path to the PDF file")
    parser.add_argument("--out", help="Output directory for .metadata.efu (if omitted, script prompts for path)")
    parser.add_argument("--type", help="Asset root type override (fixture/furniture/material/object). Auto-detected from filename if omitted.")
    parser.add_argument("--dry-run", action="store_true", help="Show final enriched rows without writing output")
    parser.add_argument("--csv", action="store_true", help="Print full CSV table to stdout (implies --dry-run)")
    parser.add_argument("--no-images", action="store_true", help="Skip product image extraction")
    parser.add_argument("--skip-ai", action="store_true", help="Skip AI enrichment (faster, but not final enriched output)")
    args = parser.parse_args()
    if args.csv:
        args.dry_run = True

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        sys.exit(1)

    root = args.type.strip().capitalize() if args.type else detect_root_from_name(pdf_path.name)

    out_dir = resolve_output_dir(pdf_path, args.out)
    out_path = out_dir / ".metadata.efu"
    album_name = _album_from_out_dir(out_dir)

    # When --csv, send all human-readable output to stderr so stdout is clean CSV
    log = sys.stderr if args.csv else sys.stdout

    print(f"Reading : {pdf_path.name}", file=log)
    rows, page_indices, project, client = extract_from_pdf(pdf_path, root)

    if not rows:
        print("ERROR: No schedule entries found. Check PDF structure.", file=log)
        sys.exit(1)

    # --- AI enrichment/cleanup ---
    if args.skip_ai:
        print("AI      : skipped (--skip-ai)", file=log)
    else:
        rows = cleanup_rows_with_ai(rows, pdf_path)

    for row in rows:
        row["Album"] = album_name

    print(f"Project : {project}", file=log)
    print(f"Client  : {client}", file=log)
    print(f"Album   : {album_name}", file=log)
    print(f"Entries : {len(rows)}", file=log)
    print(file=log)

    for r in rows:
        print(f"  {r['custom_property_6']:<12} {r['Filename']:<40} loc={r['custom_property_1']}", file=log)

    if args.dry_run:
        if args.csv:
            # Reconfigure stdout to handle UTF-8
            import io
            utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            writer = csv.DictWriter(utf8_stdout, fieldnames=EFU_FIELDNAMES, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(rows)
            utf8_stdout.flush()
        else:
            print("\n[dry-run] No file written.", file=log)
        return

    # --- Image extraction (before EFU write so Filename points to real .jpg) ---
    if not args.no_images and fitz is not None and PILImage is not None:
        doc = fitz.open(str(pdf_path))
        header_xrefs = _find_header_xrefs(doc)
        img_count = 0
        for row, page_idx in zip(rows, page_indices):
            img_bytes_list = extract_page_images(doc, page_idx, header_xrefs)
            if not img_bytes_list:
                continue
            combined = combine_images(img_bytes_list)
            if combined:
                img_path = out_dir / row["Filename"]  # Filename already ends in .jpg
                img_path.write_bytes(combined)
                img_count += 1
        doc.close()
        print(f"Images  : {img_count} saved to {out_dir}", file=log)
    elif not args.no_images:
        print("Images  : skipped (pymupdf or Pillow not available)", file=log)

    written, replaced = write_metadata_efu(rows, out_path)
    action = f"Written ({written} rows, {replaced} updated)" if replaced else f"Written ({written} rows)"
    print(f"EFU     : {action} → {out_path}", file=log)


if __name__ == "__main__":
    main()
