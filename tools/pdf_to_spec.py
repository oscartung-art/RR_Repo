"""
pdf_to_spec.py — Extract a fitment/specification table from a PDF using vision LLM + OpenRouter.

Usage:
    python tools/pdf_to_spec.py <path/to/spec.pdf> [<project.md>] [--dry-run]

    <project.md>  optional: appends/updates ### Kitchen Fitments in that file.
    --dry-run     extract and print the table to stdout only; no files written, no images fetched.

Output (beside the PDF):
    <stem>_spec.csv        — CSV: ID, Item, Model/Spec, Finish/Color, Dimension, Location, Thumbnail
    <stem>_spec_table.md   — copy-paste Markdown table
    <stem>_thumbs/         — one thumbnail per row, fetched from DDG (named by ID)

Pipeline:
    PDF  ──PyMuPDF──►  page PNG (150 DPI)
         ──OpenRouter vision LLM──►  JSON rows per page  (omitted pages return [])
         ──DDG + og:image──►  one thumbnail per row  ──►  CSV + Markdown
"""
from __future__ import annotations

import base64
import csv
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import zlib
from pathlib import Path

# Load environment variables from .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, continue without it

import fitz  # PyMuPDF

# ── OpenRouter config (reuses same env vars as ingest_asset.py) ───────────────
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY  = os.environ.get("OPENROUTER_API_KEY", "")
# gemini-2.5-flash has vision; flash-lite does NOT — keep this model for multimodal
OPENROUTER_MODEL    = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-4-scout")

# Columns extracted from spec PDF per row.
SPEC_COLUMNS = [
    "ID", "Item", "Model / Spec", "Brand", "Collection",
    "Finish / Color", "Dimension", "Location", "Mounting",
]

# EFU metadata columns — must exactly match EFU_HEADERS in ingest_asset.py.
EFU_COLUMNS = [
    "Filename", "Rating", "Tags", "URL", "From", "Mood",
    "Author", "Writer", "Album", "Genre", "People", "Company",
    "Period", "Artist", "Title", "Comment", "To", "Manager", "Subject", "CRC-32",
]

# Flat output directory for thumbnails and EFU (mirrors ingest_asset.py THUMBNAIL_BASE).
THUMBS_DIR = Path(os.environ.get("RR_DB_DIR", "D:/DB"))
EFU_PATH = THUMBS_DIR / ".metadata.efu"


# ── Name helpers (mirrors ingest_asset.py conventions) ───────────────────────

def _sanitize_name_token(value: str) -> str:
    """Convert a string to a CamelCase token safe for filenames (e.g. 'sink mixer' → 'SinkMixer')."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", value).strip()
    return "".join(p[:1].upper() + p[1:] for p in cleaned.split()) if cleaned else ""


def _clean_display_case(value: str) -> str:
    """Normalize casing while preserving mixed-case tokens and short acronyms."""
    value = str(value or "").strip()
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


def clean_spec_author(row: dict) -> str:
    """Convert raw spec text into a cleaner model-name style Author field."""
    raw = str(row.get("Model / Spec", "") or "").strip()
    if not raw or raw == "-":
        return "-"

    brand = _clean_display_case(row.get("Brand", ""))
    collection = _clean_display_case(row.get("Collection", ""))
    item = _clean_display_case(row.get("Item", ""))

    value = _clean_display_case(raw)

    paren_model = re.search(r"\(\s*model\s+([^)]+?)\s*\)", value, flags=re.IGNORECASE)
    if paren_model:
        return _clean_display_case(paren_model.group(1)) or "-"

    explicit_model = re.search(r"\bmodel\s+([A-Za-z0-9][A-Za-z0-9/\- ]{2,})", value, flags=re.IGNORECASE)
    if explicit_model:
        candidate = _clean_display_case(explicit_model.group(1).strip(" ,-()"))
        if candidate:
            return candidate

    for prefix in (brand, collection, item):
        if prefix and prefix != "-" and value.lower().startswith(prefix.lower() + " "):
            value = value[len(prefix):].strip(" ,-:/")

    if "," in value:
        first_segment = value.split(",", 1)[0].strip()
        if first_segment and (re.search(r"\d", first_segment) or len(first_segment.split()) <= 4):
            value = first_segment

    value = re.split(r"\b(?:deck mounted|wall mounted|single lever|pull-out|with\b|w/|under counter|refer to|as shown)\b", value, 1, flags=re.IGNORECASE)[0].strip(" ,-:/")
    value = re.sub(r"\s+\d{4,}$", "", value).strip()
    value = re.sub(r"\s+[A-Za-z]+/[A-Za-z][A-Za-z/ -]*$", "", value).strip()

    if value and len(value.split()) >= 7:
        leading_code = re.match(r"^([A-Z]*\d[A-Z0-9\-/]*)\b", value)
        if leading_code:
            value = leading_code.group(1)

    if brand and value.lower() == brand.lower():
        value = ""
    if collection and value.lower() == collection.lower():
        value = ""
    if item and value.lower() == item.lower():
        value = ""

    value = value.strip(" ,-:/")
    return value or "-"


def _mood_hierarchy_leaf(value: str) -> str:
    if not value or value == "-":
        return ""
    return value.strip().strip("/").split("/")[-1]


def classify_spec_mood(row: dict) -> str:
    """Classify a spec row into an ingest-style hierarchy path."""
    item = str(row.get("Item", "") or "")
    model = str(row.get("Model / Spec", "") or "")
    location = str(row.get("Location", "") or "")
    mounting = str(row.get("Mounting", "") or "")

    haystack = " ".join([item, model, location, mounting]).lower()
    compact = re.sub(r"[^a-z0-9]+", "", haystack)

    def _contains(*tokens: str) -> bool:
        for token in tokens:
            token_l = token.lower()
            token_c = re.sub(r"[^a-z0-9]+", "", token_l)
            if token_l in haystack or (token_c and token_c in compact):
                return True
        return False

    if _contains("induction hob", "inductionhob", "domino induction", "dominoinduction", "horizone domino"):
        return "Fixture/Appliance/InductionHob"
    if _contains("cookerhood", "cooker hood", "telescopic cookerhood"):
        return "Fixture/Appliance/Cookerhood"
    if _contains("steam oven", "combisteamoven", "combi steam oven"):
        return "Fixture/Appliance/SteamOven"
    if _contains("refrigerator", "fridge", "single door fridge"):
        return "Fixture/Appliance/Refrigerator"
    if _contains("washer dryer", "washerdryer"):
        return "Fixture/Appliance/WasherDryer"

    if _contains("sink mixer", "sinkmixer", "kitchen mixer", "kitchen faucet", "kitchenfaucet", "faucet"):
        return "Fixture/Kitchen/KitchenFaucet"
    if _contains("kitchen sink", "kitchensink") or (_contains("sink") and not _contains("mixer")):
        return "Fixture/Kitchen/KitchenSink"
    if _contains("waste bin", "wastebin"):
        return "Fixture/Kitchen/WasteBin"
    if _contains("ladder", "folding ladder", "foldingladder"):
        return "Fixture/Kitchen/FoldingLadder"
    if _contains("light strip", "lightstrip", "motion sensor", "motionsensor", "driver k1215e"):
        return "Fixture/Lighting/LightStrip"
    if _contains("shoe rack", "shoerack"):
        return "Fixture/Storage/ShoeRack"
    if _contains("sliding track", "slidingtrack"):
        return "Fixture/Hardware/SlidingTrack"
    if _contains("sliding tray", "slidingtray"):
        return "Fixture/Kitchen/SlidingTray"
    if _contains("cutlery tray", "cutlerytray"):
        return "Fixture/Kitchen/CutleryTray"
    if _contains("spice bottle", "spicebottle", "twin hook", "twinhook", "metal slot", "metalslot", "accessories shelf", "accessoriesshelf", "kitchen accessories", "kitchenaccessories"):
        return "Fixture/Kitchen/KitchenAccessory"

    if _contains("kitchen"):
        return "Fixture/Kitchen/KitchenAccessory"
    if _contains("cabinet", "storage", "shoe"):
        return "Fixture/Storage/StorageAccessory"
    return "Fixture/Accessory"


def build_virtual_filename(row: dict, extension: str = ".png") -> str:
    """Return a stable thumbnail-like filename without creating a file on disk."""
    mood_leaf = _mood_hierarchy_leaf(row.get("_mood_path", "") or classify_spec_mood(row))
    item_token = _sanitize_name_token(mood_leaf) or _sanitize_name_token(row.get("Item", "")) or "Item"
    model_token = _sanitize_name_token(" ".join(str(row.get("Model / Spec", "")).split()[:3]))
    id_token = _sanitize_name_token(row.get("ID", ""))

    parts: list[str] = []
    for token in (item_token, model_token, id_token):
        if token and token not in parts:
            parts.append(token)

    if not parts:
        parts = ["Item"]
    return "_".join(parts) + extension


def ensure_placeholder_file(filename: str, out_dir: Path) -> Path:
    """Ensure a zero-byte placeholder file exists for the EFU filename."""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / filename
    if not target.exists():
        target.touch()
    return target


def compute_crc32(file_path: Path) -> str:
    """Return the CRC-32 of a file as an 8-char uppercase hex string."""
    checksum = 0
    with file_path.open("rb") as fh:
        while chunk := fh.read(1024 * 1024):
            checksum = zlib.crc32(chunk, checksum)
    return f"{checksum & 0xFFFFFFFF:08X}"


# ── Thumbnail placeholder generation (replaces online fetch) ─────────────────

def _ddg_search_urls(query: str, max_results: int = 6) -> list[str]:
    """Return up to max_results URLs from a DuckDuckGo HTML search."""
    encoded = urllib.parse.quote_plus(query)
    req = urllib.request.Request(
        f"https://html.duckduckgo.com/html/?q={encoded}",
        headers={"User-Agent": "Mozilla/5.0 (compatible; SpecExtractor/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            body = r.read().decode("utf-8", errors="replace")
    except Exception:
        return []
    urls: list[str] = []
    for m in re.finditer(r'class="result__a"[^>]*href="([^"]+)"', body):
        href = html.unescape(m.group(1))
        qs = urllib.parse.urlparse(href).query
        actual = urllib.parse.parse_qs(qs).get("uddg", [href])[0]
        if actual.startswith("http"):
            urls.append(actual)
        if len(urls) >= max_results:
            break
    return urls


def _fetch_og_image(url: str) -> str:
    """Fetch a page and return the og:image URL, or '' if not found."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; SpecExtractor/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            raw = r.read(65536).decode("utf-8", errors="replace")  # only need <head>
    except Exception:
        return ""
    m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', raw, re.IGNORECASE)
    if not m:
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image', raw, re.IGNORECASE)
    if not m:
        return ""
    img_url = html.unescape(m.group(1)).strip()
    # Convert relative URLs to absolute
    if img_url.startswith(("http://", "https://")):
        return img_url
    elif img_url.startswith("//"):
        return "https:" + img_url
    elif img_url.startswith("/"):
        # Join with base URL
        parsed = urllib.parse.urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{img_url}"
    else:
        # Relative path without leading slash
        return urllib.parse.urljoin(url, img_url)


def _download_image(url: str, dest: Path) -> bool:
    """Download an image URL to dest. Returns True on success."""
    # Ensure URL is absolute
    if not url.startswith(("http://", "https://")):
        return False
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; SpecExtractor/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        if len(data) < 2000:   # suspiciously small — likely an error page
            return False
        dest.write_bytes(data)
        return True
    except Exception:
        return False


def fetch_thumbnail_for_row(row: dict, out_dir: Path) -> str:
    """
    Create a placeholder thumbnail image with text overlay for the spec item.
    Returns canonical EFU filename (pattern: MoodToken_ModelShort_CRC32.png)
    and stores CRC-32 in row['_thumb_crc32'].
    Uses Pillow (PIL) if available, otherwise creates a .txt placeholder.
    """
    item  = row.get("Item", "-").strip()
    model = row.get("Model / Spec", "-").strip()
    rid   = re.sub(r"[^A-Za-z0-9_-]", "_", row.get("ID", "item").strip()) or "item"
    
    mood = _sanitize_name_token(item) or "Item"
    model_short = _sanitize_name_token(" ".join(model.split()[:3])) or "Spec"
    
    # Create placeholder image
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        
        # Create a 400x300 placeholder image
        width, height = 400, 300
        img = Image.new('RGB', (width, height), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        
        # Try to load a font, fall back to default
        try:
            font = ImageFont.truetype("arial.ttf", 20)
            small_font = ImageFont.truetype("arial.ttf", 14)
        except:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Draw title
        title = f"{rid}: {item}"
        title_lines = textwrap.wrap(title, width=30)
        y_text = 20
        for line in title_lines:
            draw.text((20, y_text), line, font=font, fill=(0, 0, 0))
            y_text += 30
        
        # Draw model/spec
        model_lines = textwrap.wrap(model, width=40)
        y_text += 10
        for line in model_lines[:4]:  # Limit to 4 lines
            draw.text((20, y_text), line, font=small_font, fill=(80, 80, 80))
            y_text += 20
        
        # Draw border
        draw.rectangle([5, 5, width-5, height-5], outline=(200, 200, 200), width=2)
        
        # Save to temp file
        tmp = out_dir / f"{rid}_placeholder.png"
        img.save(tmp, "PNG")
        
        # Rename to canonical EFU-compatible filename: MoodToken_ModelShort_CRC32.png
        crc = compute_crc32(tmp)
        final_name = f"{mood}_{model_short}_{crc}.png"
        final_path = out_dir / final_name
        tmp.rename(final_path)
        row["_thumb_crc32"] = crc
        return final_name
        
    except ImportError:
        # PIL not available, create a simple text file as placeholder
        tmp = out_dir / f"{rid}_placeholder.txt"
        content = f"{rid}: {item}\\n{model}"
        tmp.write_text(content, encoding="utf-8")
        
        crc = compute_crc32(tmp)
        final_name = f"{mood}_{model_short}_{crc}.txt"
        final_path = out_dir / final_name
        tmp.rename(final_path)
        row["_thumb_crc32"] = crc
        return final_name
    except Exception as e:
        print(f"  WARNING: Failed to create placeholder for {rid}: {e}")
        return "-"


# ── PDF rendering ─────────────────────────────────────────────────────────────

def render_pages(pdf_path: Path, dpi: int = 150) -> list[tuple[int, str]]:
    """Render every page of the PDF to a base64 PNG string at the given DPI.

    Returns a list of (1-based page_no, b64_png) tuples.
    """
    doc = fitz.open(str(pdf_path))
    pages: list[tuple[int, str]] = []
    for i in range(doc.page_count):
        page = doc[i]
        pix = page.get_pixmap(dpi=dpi)
        b64 = base64.b64encode(pix.tobytes("png")).decode()
        pages.append((i + 1, b64))
    doc.close()
    return pages


# ── OpenRouter call (multimodal-capable) ──────────────────────────────────────

def _call_openrouter(messages: list[dict], model: str, api_key: str, timeout: int = 180) -> str:
    """Send a messages list to OpenRouter and return the raw text reply."""
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
    }
    req = urllib.request.Request(
        OPENROUTER_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = ""
        try:
            details = exc.read().decode("utf-8", errors="replace")[:400]
        except Exception:
            details = str(exc)
        if exc.code == 402:
            print(f"\nERROR: OpenRouter credits exhausted (HTTP 402).\nDetails: {details}", flush=True)
            raise SystemExit(1)
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {details}") from exc

    try:
        return (body["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError):
        return ""


def extract_rows_from_page(page_no: int, b64_png: str, api_key: str, model: str) -> list[dict]:
    """Send one rendered PDF page to the vision LLM and return extracted spec rows."""
    cols_str = ", ".join(f'"{c}"' for c in SPEC_COLUMNS)
    prompt = (
        f"This is page {page_no} of a construction fitment specification PDF.\n"
        f"Extract every specification item visible in the table(s) on this page.\n"
        f"Return a JSON array of objects. Each object must have exactly these keys: {cols_str}.\n"
        f"Rules:\n"
        f"  - 'ID' is the item reference number (e.g. KF-01, SF-01).\n"
        f"  - 'Item' is the descriptive name of the fitment (e.g. Sink Mixer, Toilet).\n"
        f"  - 'Model / Spec' is the product model number, catalogue code, or specification text.\n"
        f"  - 'Finish / Color' is the surface finish, colour, or material description.\n"
        f"  - 'Dimension' is the size or 'As Shown' if not stated.\n"
        f"  - 'Location' is the room or zone (e.g. Kitchen, Master Bathroom).\n"
        f"  - 'Brand' is the manufacturer name extracted from the model/spec text (e.g. Hansgrohe, Kumeis). '-' if not determinable.\n"
        f"  - 'Collection' is the product series or collection name (e.g. Talis M54). '-' if not stated.\n"
        f"  - 'Mounting' is the installation form (e.g. deck-mounted, under-counter, wall-mounted, built-in, freestanding). '-' if not determinable.\n"
        f"  - Use '-' for any field not present in the source.\n"
        f"  - Do NOT invent data. Extract only what is explicitly shown.\n"
        f"  - Omit header rows, section titles, notes, and page number text - items only.\n"
        f"  - If the page is a cover, is blank, or is marked Omitted / Intentionally Blank, "
        f"return an empty array [].\n"
        f"Return ONLY compact JSON - no markdown fences, no explanation."
    )
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_png}"}},
            ],
        }
    ]
    raw_reply = _call_openrouter(messages, model, api_key)

    # Strip markdown fences if present.
    raw_reply = re.sub(r"^```(?:json)?", "", raw_reply.strip(), flags=re.IGNORECASE).strip()
    raw_reply = re.sub(r"```$", "", raw_reply).strip()

    # Repair common truncation: model omits the opening `[{` or `{"
    if raw_reply and not raw_reply.startswith(("[", "{")):
        # Looks like a dict body - try wrapping as a single-object array
        candidate = "[{" + raw_reply
        # Ensure it closes properly
        if not candidate.rstrip().endswith("]"):
            candidate = candidate.rstrip().rstrip(",") + "]"
        raw_reply = candidate

    raw_reply = re.sub(r'^\[\{(?!")([A-Za-z_][A-Za-z0-9_ /-]*")', r'[{"\1', raw_reply)

    try:
        parsed = json.loads(raw_reply)
        if isinstance(parsed, list):
            return parsed
        elif isinstance(parsed, dict):
            return [parsed]
    except json.JSONDecodeError as exc:
        print(f"  WARNING: JSON parse error on page {page_no}: {exc}", flush=True)
        print(f"  Raw reply (first 300): {raw_reply[:300]}", flush=True)
    return []


# ── EFU output helpers ────────────────────────────────────────────────────────

def _spec_to_efu_row(row: dict, project_code: str, pdf_crc32: str) -> dict:
    """Map a spec row dict to an EFU metadata row (matches EFU_HEADERS in ingest_asset.py)."""
    mood = row.get("_mood_path", "") or classify_spec_mood(row)
    return {
        "Filename": row.get("_thumb_filename", ""),
        "Rating":   "",
        "Tags":     "",
        "URL":      row.get("ID", "-"),
        "From":     "",
        "Mood":     mood,
        "Author":   clean_spec_author(row),
        "Writer":   row.get("Brand", "-"),
        "Album":    row.get("Collection", "-"),
        "Genre":    row.get("Finish / Color", "-"),
        "People":   row.get("Location", "-"),
        "Company":  row.get("Mounting", "-"),
        "Period":   "-",
        "Artist":   row.get("Dimension", "-"),
        "Title":    project_code or "-",
        "Comment":  "",
        "To":       "",
        "Manager":  "Schedule",
        "Subject":  pdf_crc32,
        "CRC-32":   row.get("_thumb_crc32", ""),
    }

def write_efu(efu_rows: list[dict], out_path: Path) -> None:
    """Append spec rows to the shared .metadata.efu (same file used by ingest_asset.py).
    Creates the file with headers if it doesn't exist yet.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = out_path.exists()
    with out_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EFU_COLUMNS)
        if not file_exists:
            writer.writeheader()
        for row in efu_rows:
            writer.writerow({
                k: row.get(k, "-") if row.get(k, "") != "" or k in {"Filename", "CRC-32"} else "-"
                for k in EFU_COLUMNS
            })
    print(f"  EFU appended ({len(efu_rows)} rows): {out_path}", flush=True)


# ── Output helpers ────────────────────────────────────────────────────────────

def write_csv(rows: list[dict], out_path: Path) -> None:
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SPEC_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  CSV written: {out_path}", flush=True)


def write_markdown_table(rows: list[dict], out_path: Path) -> None:
    def _cell(v: str) -> str:
        return v.replace("|", "\\|")

    header = "| " + " | ".join(SPEC_COLUMNS) + " |"
    divider = "| " + " | ".join("---" for _ in SPEC_COLUMNS) + " |"
    lines = [header, divider]
    for row in rows:
        lines.append("| " + " | ".join(_cell(row.get(c, "-")) for c in SPEC_COLUMNS) + " |")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  Markdown table written: {out_path}", flush=True)


def update_project_md(rows: list[dict], md_path: Path, section_title: str = "Kitchen Fitments") -> None:
    """
    Replace (or append) the spec table under ## Specifications > ### <section_title> in the
    project markdown file.  Creates the section if it doesn't exist.
    """
    md_text = md_path.read_text(encoding="utf-8")

    # Build the new table block.
    def _cell(v: str) -> str:
        return v.replace("|", "\\|")

    header  = "| " + " | ".join(SPEC_COLUMNS) + " |"
    divider = "| " + " | ".join("---" for _ in SPEC_COLUMNS) + " |"
    table_lines = [header, divider]
    for row in rows:
        table_lines.append("| " + " | ".join(_cell(row.get(c, "-")) for c in SPEC_COLUMNS) + " |")
    new_block = "\n".join(table_lines)

    # Look for an existing ### <section_title> block and replace its table.
    section_re = re.compile(
        rf"(### {re.escape(section_title)}\n)"   # heading
        rf"(\|.*?\n)+",                            # existing table rows
        re.MULTILINE,
    )
    if section_re.search(md_text):
        md_text = section_re.sub(rf"\g<1>{new_block}\n", md_text)
    else:
        # Append under ## Specifications, or at the end.
        spec_re = re.compile(r"(## Specifications\n)", re.MULTILINE)
        if spec_re.search(md_text):
            md_text = spec_re.sub(
                rf"\g<1>\n### {section_title}\n{new_block}\n",
                md_text,
            )
        else:
            md_text += f"\n\n## Specifications\n\n### {section_title}\n{new_block}\n"

    md_path.write_text(md_text, encoding="utf-8")
    print(f"  Project MD updated: {md_path}", flush=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def _print_table(rows: list[dict]) -> None:
    """Print rows as a plain-text table to stdout."""
    preview_cols = list(SPEC_COLUMNS)
    widths = {c: len(c) for c in preview_cols}
    for row in rows:
        for c in preview_cols:
            widths[c] = max(widths[c], len(row.get(c, "-")))
    sep = "+" + "+".join("-" * (widths[c] + 2) for c in preview_cols) + "+"
    header = "|" + "|".join(f" {c:{widths[c]}} " for c in preview_cols) + "|"
    print(sep)
    print(header)
    print(sep)
    for row in rows:
        print("|" + "|".join(f" {row.get(c, '-'):{widths[c]}} " for c in preview_cols) + "|")
    print(sep)


def main() -> None:
    args = [a.strip('"').strip() for a in sys.argv[1:]]

    # Check for help flag
    if any(a in ("-h", "--help") for a in args):
        print(__doc__)
        sys.exit(0)

    if not args:
        pdf_input = input("PDF path: ").strip().strip('"').strip()
        args = [pdf_input]

    dry_run = "--dry-run" in args
    # Extract --project CODE or --project=CODE
    project_code = next((a.split("=", 1)[1] for a in args if a.startswith("--project=")), "")
    if not project_code:
        idx = next((i for i, a in enumerate(args) if a == "--project"), -1)
        if idx >= 0 and idx + 1 < len(args):
            project_code = args[idx + 1]
    
    # Filter out flags but keep track of original args for error checking
    # We need to also skip the argument after --project if it's not a flag
    filtered_args = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("-h", "--help", "--dry-run"):
            i += 1
        elif arg == "--project":
            i += 2  # Skip --project and its value
        elif arg.startswith("--project="):
            i += 1  # Skip --project=value
        else:
            filtered_args.append(arg)
            i += 1
    
    if not filtered_args:
        print("ERROR: No PDF file specified.")
        print("Usage: python tools/pdf_to_spec.py <path/to/spec.pdf> [--project CODE] [--dry-run]")
        print("       python tools/pdf_to_spec.py -h  # Show help")
        sys.exit(1)
    
    pdf_path = Path(filtered_args[0])
    if not pdf_path.exists():
        print(f"ERROR: File not found: {pdf_path}")
        sys.exit(1)
    if pdf_path.suffix.lower() != ".pdf":
        print(f"ERROR: Not a PDF file: {pdf_path}")
        print("Please provide a .pdf file.")
        sys.exit(1)

    # Check API key early
    api_key = OPENROUTER_API_KEY.strip()
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY is not set.")
        print("Set it in your .env file or environment variable.")
        print("Example .env: OPENROUTER_API_KEY=\"your-key-here\"")
        sys.exit(1)

    project_md: Path | None = Path(filtered_args[1]) if len(filtered_args) >= 2 else None
    if project_md and not project_md.exists():
        print(f"Project MD not found: {project_md}")
        project_md = None

    base = pdf_path.stem
    model = OPENROUTER_MODEL.strip() or "meta-llama/llama-4-scout"
    pdf_crc32 = compute_crc32(pdf_path)

    print(f"\nPDF:   {pdf_path}")
    print(f"Model: {model}")
    if project_code:
        print(f"Project: {project_code}")
    if dry_run:
        print("Mode:  --dry-run (no files written)")
    print()

    # Step 1 - render all pages to PNG
    print("Step 1/2 - rendering PDF pages ...")
    pages = render_pages(pdf_path)
    print(f"  {len(pages)} pages rendered.\n")

    # Step 2 - vision LLM processes each page
    print("Step 2/2 - extracting rows via vision LLM ...")
    all_rows: list[dict] = []
    for page_no, b64_png in pages:
        print(f"  [page {page_no}/{len(pages)}] ...", end=" ", flush=True)
        rows = extract_rows_from_page(page_no, b64_png, api_key, model)
        # Normalize: ensure every row has all columns
        for row in rows:
            all_rows.append({col: str(row.get(col, "") or "-").strip() for col in SPEC_COLUMNS})
        print(f"{len(rows)} rows")

    print(f"\n  {len(all_rows)} total rows extracted.\n")

    if not all_rows:
        print("No rows extracted - check the PDF or try a different model.")
        sys.exit(1)

    # Always print to console
    _print_table(all_rows)

    if dry_run:
        print("\n[dry-run] No files written.")
        return

    for row in all_rows:
        row["_mood_path"] = classify_spec_mood(row)
        row["_thumb_filename"] = build_virtual_filename(row)
        row["_thumb_crc32"] = ""
        ensure_placeholder_file(row["_thumb_filename"], THUMBS_DIR)

    # Write outputs
    print()
    write_csv(all_rows, pdf_path.with_name(f"{base}_spec.csv"))
    write_markdown_table(all_rows, pdf_path.with_name(f"{base}_spec_table.md"))

    efu_rows = [_spec_to_efu_row(r, project_code, pdf_crc32) for r in all_rows]
    write_efu(efu_rows, EFU_PATH)

    if project_md:
        update_project_md(all_rows, project_md, section_title="Kitchen Fitments")

    print("\nDone.")


if __name__ == "__main__":
    main()
