"""
enrich_gdrive.py  —  Unified AI enrichment pipeline for the furniture/architecture asset database.

Reads rows from CurrentDB Google Sheet, downloads images from Google Drive,
analyzes them with Gemini 2.5 Flash, and writes enriched metadata back to the Sheet.

Usage:
    python3.11 enrich_gdrive.py [--test N] [--types TYPE1,TYPE2,...] [--start-row N]

Options:
    --test N        Process only N randomly sampled rows (default: 100 for test mode)
    --types         Comma-separated list of URL types to process (default: all)
    --start-row N   Resume from a specific sheet row number (1-indexed, excluding header)
    --full          Run full production batch (all rows)
    --dry-run       Parse and plan without calling AI or writing to sheet

Examples:
    python3.11 enrich_gdrive.py --test 100          # 100-row random sample
    python3.11 enrich_gdrive.py --types Furniture   # All Furniture rows
    python3.11 enrich_gdrive.py --full              # All 40,000+ rows
"""

import os
import re
import sys
import json
import base64
import random
import argparse
import tempfile
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
SPREADSHEET_ID  = "1yA65ahfpUmym4sFnT2bQfKg1YumhW5Z9pzaoxmlBAi4"
SHEET_NAME      = "CurrentDB"
DRIVE_INDEX     = "/home/ubuntu/drive_file_index.json"
DB_ROWS_CACHE   = "/home/ubuntu/currentdb_rows.json"

MODEL           = "gemini-2.5-flash"
MAX_WORKERS     = 8         # Parallel AI calls (reduced to stay under 200 RPM rate limit)
BATCH_WRITE_SZ  = 50        # Write to sheet every N rows
MAX_RETRIES     = 5         # Max retries for 429 rate limit errors
RETRY_BASE_WAIT = 15        # Base wait seconds for exponential backoff

client = OpenAI()

# ---------------------------------------------------------------------------
# AUTO-REFRESH RCLONE TOKEN FROM ENV VAR
# The GOOGLE_DRIVE_TOKEN env var is refreshed by the platform on each task start.
# We inject it into the rclone config so downloads work without manual reconnection.
# ---------------------------------------------------------------------------
def refresh_rclone_token():
    """Update rclone config with the current GOOGLE_DRIVE_TOKEN env var."""
    token = os.environ.get("GOOGLE_DRIVE_TOKEN", "")
    if not token:
        return  # No token available, leave config as-is
    rclone_token = json.dumps({
        "access_token": token,
        "token_type": "Bearer",
        "expiry": "2099-01-01T00:00:00Z"
    })
    config_content = f"""[manus_google_drive]
type = drive
scope = drive
token = {rclone_token}
"""
    try:
        with open("/home/ubuntu/.gdrive-rclone.ini", "w") as f:
            f.write(config_content)
    except Exception:
        pass

refresh_rclone_token()  # Refresh token at startup

# ---------------------------------------------------------------------------
# COLUMN MAPPING  (0-indexed, matching sheet header order)
# A=0  B=1  C=2  D=3  E=4  F=5  G=6  H=7  I=8  J=9  K=10 L=11 M=12 N=13 O=14 P=15 Q=16 R=17 S=18
# Rating Tags Filename URL From Mood Author Writer Album Genre People Company Period Artist Title Comment To Manager Subject
# ---------------------------------------------------------------------------
COL = {
    "Rating":   0,  "Tags":    1,  "Filename": 2,  "URL":     3,
    "From":     4,  "Mood":    5,  "Author":   6,  "Writer":  7,
    "Album":    8,  "Genre":   9,  "People":  10,  "Company": 11,
    "Period":  12,  "Artist":  13, "Title":   14,  "Comment": 15,
    "To":      16,  "Manager": 17, "Subject": 18,
}
TOTAL_COLS = 19

# Columns that will be written back (by name)
WRITE_COLS = ["From", "Mood", "Author", "Writer", "Album", "Genre",
              "People", "Company", "Period", "Artist", "Comment", "To",
              "Manager", "Tags"]

# ---------------------------------------------------------------------------
# BRAND NAME NORMALISATION
# ---------------------------------------------------------------------------
BRAND_FIXES = {
    "b&b italia":           "BBItalia",
    "b&bitalia":            "BBItalia",
    "carl hansen & son":    "CarlHansenAndSon",
    "carl hansen&son":      "CarlHansenAndSon",
    "carlhansenandson":     "CarlHansenAndSon",
    "restoration hardware": "RestorationHardware",
    "restorationhardware":  "RestorationHardware",
}

def fix_brand(name: str) -> str:
    key = name.lower().strip()
    if key in BRAND_FIXES:
        return BRAND_FIXES[key]
    name = name.replace("&", "And")
    parts = name.split()
    return "".join(p[0].upper() + p[1:] if p else "" for p in parts)

# ---------------------------------------------------------------------------
# AI PROMPTS  (one per asset group)
# ---------------------------------------------------------------------------
PROMPTS = {

    "Furniture": """Analyze this furniture product image and return the following fields.
IMPORTANT: All fields marked [PascalCase] must use PascalCase with NO spaces.
If a field cannot be determined, write exactly: Unknown

Mood [PascalCase]: <Furniture subcategory — e.g., Armchair, DiningChair, Sofa, CoffeeTable, Bed, Barstool, SideTable>
Writer [PascalCase]: <Brand name — e.g., Dedon, BBItalia, RestorationHardware, CarlHansenAndSon. Replace & with And.>
Album [PascalCase]: <Collection or Product Line name if identifiable, otherwise Unknown>
Location [PascalCase]: <Primary usage location — e.g., Outdoor, LivingRoom, Bedroom, Bathroom, Kitchen, DiningRoom, Office, KidsRoom>
Material [PascalCase]: <Primary visible material — e.g., Wood, Metal, Leather, Fabric, Plastic, Glass, Rattan, Marble>
Style [PascalCase]: <Visual style — e.g., Modern, Minimal, Classic, Industrial, Scandinavian, Rustic, Contemporary>
Shape [PascalCase]: <Overall form in ONE word — e.g., Round, Rectangular, LShaped, Curved, Square, Oval>
Color [PascalCase]: <Primary color of the furniture — e.g., White, DarkGrey, NaturalWood, OffWhite, NavyBlue, Beige>
Author: <SKU or Model Number if clearly visible, otherwise Unknown>
Tags [PascalCase, comma-separated]: <Keywords NOT covered by other fields — e.g., Stackable, Foldable, Upholstered, ArmRest, Swivel, Adjustable>
Comment: <One clear English sentence describing the furniture piece.>""",

    "Fixture": """Analyze this fixture/appliance/plumbing/lighting image and return the following fields.
IMPORTANT: All fields marked [PascalCase] must use PascalCase with NO spaces.
If a field cannot be determined, write exactly: Unknown

Mood [PascalCase]: <Specific fixture subcategory — e.g., PendantLight, Refrigerator, BathroomSink, CeilingFan, Toilet, Door, Railing, KitchenFaucet>
Writer [PascalCase]: <Brand name if visible — e.g., Samsung, Grohe, Toto, Kohler, Dyson, Panasonic>
Album [PascalCase]: <Product or Model Name if identifiable, otherwise Unknown>
Location [PascalCase]: <Primary room/location — e.g., Kitchen, Bathroom, LivingRoom, Outdoor, Gym, Office, Bedroom>
Material [PascalCase]: <Primary visible material — e.g., Steel, Chrome, Ceramic, Glass, Plastic, Brass, Wood>
Style [PascalCase]: <Visual style — e.g., Modern, Industrial, Classic, Minimal, Contemporary>
Color [PascalCase]: <Primary color — e.g., White, Chrome, MatteBlack, BrushedSteel, Gold>
Shape [PascalCase]: <Physical form — e.g., Pendant, Recessed, Linear, Chandelier, WallMounted, Freestanding, Cylindrical>
Author: <SKU or Model Number if clearly visible, otherwise Unknown>
Tags [PascalCase, comma-separated]: <Supplementary keywords — e.g., SmartHome, Touchless, EnergyEfficient, Dimmable, BuiltIn>
Comment: <One clear English sentence describing the fixture.>""",

    "Vegetation": """Analyze this vegetation/plant image and return the following fields.
IMPORTANT: All fields must use PascalCase with NO spaces, except Comment.
If a field cannot be determined, write exactly: Unknown

PlantType: <general type — e.g., Tree, Shrub, Flower, Grass, PottedPlant, Succulent, Creeper>
LatinName: <scientific name if identifiable — e.g., AcerPalmatum, GinkgoBiloba. Otherwise Unknown>
CommonName: <common English name — e.g., JapaneseMaple. Otherwise Unknown>
Location: <where it grows — e.g., Indoor, Outdoor, Tropical, Desert>
Season: <seasonal appearance — e.g., Evergreen, Deciduous, Flowering, Autumn>
Style: <visual style — e.g., Realistic, Stylized, LowPoly>
Color: <dominant foliage/flower color — e.g., Green, DarkGreen, Autumn, Purple>
Form: <growth form — e.g., Upright, Spreading, Weeping, Columnar, Bushy>
Height: <approximate height range in metric — e.g., 0.5-1m, 3-5m, 10-20m>
Tags: <comma-separated PascalCase keywords — e.g., Animated, Conifer, Bamboo>
Comment: <one natural sentence describing the plant>""",

    "Material": """Analyze this material texture thumbnail and return the following fields.
IMPORTANT: All fields must use PascalCase with NO spaces, except Comment.
If a field cannot be determined, write exactly: Unknown

MaterialName: <specific material name — e.g., RoughConcrete, WoodenPlanks, BrickFacade>
MaterialCategory: <top-level category — e.g., Concrete, Wood, Stone, Metal, Fabric, Soil>
Surface: <surface finish — e.g., Rough, Smooth, Polished, Weathered, Painted>
Color: <dominant color — e.g., Grey, Brown, Beige, White, Rust>
Pattern: <texture pattern — e.g., Seamless, Tiled, Random, Striped, Herringbone>
Tags: <comma-separated PascalCase keywords — e.g., Outdoor, Wet, Aged, Stained, Damaged>
Comment: <one natural sentence describing the material texture>""",

    "People": """Analyze this image of a person (cutout or 3D model) and return the following fields.
IMPORTANT: All fields must use PascalCase with NO spaces, except Comment.
If a field cannot be determined, write exactly: Unknown

Gender: <Male or Female>
Ethnicity: <e.g., Chinese, Black, European, Arab, SouthAsian>
AgeGroup: <e.g., Adult, Child, Elderly, Teen>
Pose: <pose or activity — e.g., Standing, Walking, Sitting, Running, Talking>
Clothing: <clothing style — e.g., Casual, Business, Formal, Sportswear, Swimwear>
Color: <dominant clothing color — e.g., White, Black, Blue, Red>
Location: <suggested scene context — e.g., Office, Street, Beach, Indoor>
Tags: <comma-separated PascalCase keywords — e.g., WithBag, WithPhone, Couple, Group>
Comment: <one natural sentence describing the person>""",

    "FurnitureLike": """Analyze this product/object image and return the following fields.
IMPORTANT: All fields must use PascalCase with NO spaces, except Comment.
If a field cannot be determined, write exactly: Unknown

Subcategory: <specific item type — e.g., Vase, iPhone, TennisBall, Sneaker, SportsCar>
Brand: <brand if visible — e.g., Apple, Nike, Ferrari, Ikea>
ProductName: <product/model name if identifiable — e.g., iPhone15Pro, AirMax>
Location: <where it belongs/is used — e.g., Kitchen, LivingRoom, Gym, Outdoor>
Material: <primary material — e.g., Glass, Ceramic, Aluminum, Rubber>
Style: <visual style — e.g., Modern, Classic, Industrial, Sporty>
Color: <primary color — e.g., White, Black, Chrome, Red>
Shape: <physical form — e.g., Round, Rectangular, Cylindrical>
Tags: <comma-separated PascalCase keywords — e.g., Wireless, Foldable, Touchscreen>
Comment: <one natural sentence describing the object>""",

    "Buildings": """Analyze this architectural/building element image and return the following fields.
IMPORTANT: All fields must use PascalCase with NO spaces, except Comment.
NOTE: Do NOT extract color from this image — the background may be a diagram with non-representative colors.
If a field cannot be determined, write exactly: Unknown

Subcategory: <specific architectural element — e.g., DoorHandle, ExteriorDoor, Skylight, Fence, StoneColumn>
Material: <primary material — e.g., Wood, Steel, Glass, Concrete, Brick>
Style: <visual style — e.g., Modern, Classic, Industrial, Gothic>
Form: <physical form or operation — e.g., Lever, Sliding, Hinged, Arched, Flat>
Tags: <comma-separated PascalCase keywords — e.g., Exterior, Interior, Structural, Decorative>
Comment: <one natural sentence describing the architectural element>""",

    "Layouts": """Analyze this floor plan/layout arrangement image and return the following fields.
IMPORTANT: All fields must use PascalCase with NO spaces, except Comment.
If a field cannot be determined, write exactly: Unknown

LayoutType: <specific layout type — e.g., DiningTable, Seating, LivingRoom, PrivateOffice>
RoomType: <room/space type — e.g., DiningRoom, LivingRoom, Office, Outdoor>
ApproxSize: <approximate footprint size in metric — e.g., 2x2m, 3x4m, 6x8m>
Shape: <layout shape — e.g., Linear, UShaped, LShaped, Circular, Square>
Tags: <comma-separated PascalCase keywords — e.g., Outdoor, Modular, Compact, HighDensity>
Comment: <one natural sentence describing the layout, including approximate size and context>""",
}

# ---------------------------------------------------------------------------
# URL -> ASSET GROUP MAPPING
# ---------------------------------------------------------------------------
def get_asset_group(url: str) -> str:
    u = url.lower().strip()
    if u == "furniture":              return "Furniture"
    if u == "fixture":                return "Fixture"
    if u == "vegetation":             return "Vegetation"
    if u in ("material", "texture"):  return "Material"
    if u == "people":                 return "People"
    if u in ("object", "objects", "digital", "sports", "apparel", "vehicle"):
        return "FurnitureLike"
    if u == "buildings":              return "Buildings"
    if u in ("layouts", "layout"):    return "Layouts"
    return None  # Skip unknown types

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
_lock = threading.Lock()

def parse_field(text: str, field_name: str) -> str:
    """Extract a field value from the AI response."""
    # Pattern 1: standard format with colon - "FieldName [optional]: value"
    # Pattern 2: no-colon format - "FieldName value" (AI sometimes omits the colon)
    pattern = rf"^{re.escape(field_name)}\s*(?:\[[^\]]*\])?\s*:?\s*(.+?)(?=\n[A-Z][a-zA-Z]+\s*(?:\[[^\]]*\])?\s*:?\s|$)"
    match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE | re.DOTALL)
    if match:
        val = match.group(1).strip()
        val = re.sub(r"\s+", " ", val)
        if val.lower() in ("unknown", "n/a", ""):
            return ""
        # Reject values that look like shifted field-name artifacts
        # e.g. "Writer [Unknown]:" or "Location [LivingRoom]:" ending with ":"
        if re.match(r'^[A-Za-z]+\s*\[[^\]]*\]\s*:?\s*$', val):
            return ""
        # Also reject if value contains embedded field patterns like "Writer [X]:Location [Y]:"
        if re.search(r'[A-Za-z]+\s*\[[^\]]+\]\s*:', val):
            return ""
        return val
    return ""

def extract_unique_id(filename: str) -> str:
    """Build a unique ID from filename: {TopFolder}{NumericID}
    e.g. '3Dsky\\10-03 1029458.jpg' -> '3Dsky1029458'
    Fixes the '3Dsky3Dsky' duplication by using only the top-level folder name once.
    """
    parts = filename.replace('\\', '/').split('/')
    # Top-level folder (e.g. '3Dsky', 'Quixel', 'Dimensions')
    top_folder = re.sub(r'[^a-zA-Z0-9]', '', parts[0]) if len(parts) > 1 else ""
    # Numeric ID from filename stem (prefer 5+ digit sequences)
    stem = os.path.splitext(os.path.basename(filename))[0]
    nums = re.findall(r'\d{5,}', stem)
    if nums:
        num_id = nums[0]
    else:
        # Fallback: alphanumeric chars from stem, last 10
        num_id = re.sub(r'[^a-zA-Z0-9]', '', stem)[-10:]
    return f"{top_folder}{num_id}"

def to_pascal(text: str) -> str:
    if not text:
        return text
    parts = re.sub(r'[^a-zA-Z0-9]', ' ', text).split()
    return "".join(p[0].upper() + p[1:] if p else "" for p in parts)

def get_row_value(row: list, col_name: str) -> str:
    idx = COL[col_name]
    if idx < len(row):
        return str(row[idx]).strip()
    return ""

# ---------------------------------------------------------------------------
# GOOGLE DRIVE IMAGE FETCHER
# ---------------------------------------------------------------------------
_drive_index = None

def load_drive_index():
    global _drive_index
    if _drive_index is None:
        with open(DRIVE_INDEX) as f:
            raw = json.load(f)
        # Build normalized lookup (forward slashes, case-insensitive)
        # Primary lookup uses exact case; fallback uses lowercase
        exact = {k.replace('\\', '/'): v for k, v in raw.items()}
        lower = {k.lower(): v for k, v in exact.items()}
        _drive_index = (exact, lower)
    return _drive_index

def fetch_image_b64(filename: str, tmp_dir: str) -> tuple:
    """Download image from Drive and return (base64_string, mime_type).
    Returns (None, None) on failure.
    """
    exact_idx, lower_idx = load_drive_index()
    normalized = filename.replace('\\', '/')
    file_id = exact_idx.get(normalized) or lower_idx.get(normalized.lower())

    if not file_id:
        # Fallback: try prefix match for filenames with truncated/missing extensions
        # Cases:
        #   DB has "...5dd2d7ebd8e23."  (trailing dot)   -> Drive has "...jpeg"
        #   DB has "...thumb.jp"         (truncated .jpg) -> Drive has "...thumb.jpg"
        #   DB has "...thumb.jpe"        (truncated .jpeg)-> Drive has "...thumb.jpeg"
        # Strategy: strip any partial extension suffix and do a prefix match
        import re as _re
        # Remove trailing partial extension: strip trailing dot or partial image ext
        norm_stripped = _re.sub(r'\.(jpe?g?|png?|webp?|gif?|bmp?)?$', '', normalized, flags=_re.IGNORECASE)
        if norm_stripped != normalized:
            # Try to find a matching key by prefix in the exact index
            for candidate_key, candidate_id in exact_idx.items():
                if candidate_key.startswith(norm_stripped + '.'):
                    file_id = candidate_id
                    filename = candidate_key  # use the full filename with extension
                    normalized = candidate_key
                    break
            if not file_id:
                norm_lower = norm_stripped.lower()
                for candidate_key, candidate_id in lower_idx.items():
                    if candidate_key.startswith(norm_lower + '.'):
                        file_id = candidate_id
                        filename = candidate_key
                        normalized = candidate_key
                        break

    if not file_id:
        return None, None

    # Determine output filename
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', os.path.basename(normalized))
    out_path = os.path.join(tmp_dir, safe_name)

    # Use rclone for reliable downloads (handles auth refresh automatically)
    RCLONE_CONFIG = "/home/ubuntu/.gdrive-rclone.ini"
    RCLONE_ROOT_ID = "1TNwfOEaOPYcZe9vXvfegMqkC2wU3QG2T"  # My Drive 'Database' folder
    rclone_src = f"manus_google_drive:/{normalized}"
    result = subprocess.run(
        ["rclone", "copyto", rclone_src, out_path,
         "--config", RCLONE_CONFIG,
         "--drive-root-folder-id", RCLONE_ROOT_ID,
         "--retries", "3"],
        capture_output=True, text=True
    )

    if result.returncode != 0 or not os.path.exists(out_path):
        return None, None

    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    mime_type = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

    try:
        with open(out_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        os.remove(out_path)
        return b64, mime_type
    except Exception:
        return None, None

# ---------------------------------------------------------------------------
# PER-ROW AI ANALYSIS
# ---------------------------------------------------------------------------
def analyze_row(sheet_row_idx: int, row: list, tmp_dir: str) -> dict:
    """Analyze one row. Returns dict of column_name -> value, or {'error': msg}."""
    filename = get_row_value(row, "Filename")
    url_type = get_row_value(row, "URL")
    asset_group = get_asset_group(url_type)

    if not asset_group:
        return {"error": f"Unknown URL type: {url_type!r}"}

    if not filename:
        return {"error": "Empty filename"}

    # Fetch image
    b64, mime_type = fetch_image_b64(filename, tmp_dir)
    if not b64:
        return {"error": f"Image not found in Drive: {filename}"}

    # Build prompt with existing context
    prompt = PROMPTS[asset_group]

    # Add context hints from existing DB values
    existing_mood = get_row_value(row, "Mood")
    if existing_mood and existing_mood.lower() not in ("", "nan", "filename", "unknown"):
        prompt += f"\n\nContext: Existing subcategory hint: '{existing_mood}'. Standardize to PascalCase."

    # Call AI with exponential backoff retry for rate limits
    import time
    content = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                        {"type": "text", "text": prompt}
                    ]
                }],
                max_tokens=400
            )
            content = response.choices[0].message.content
            break  # Success
        except Exception as e:
            err_str = str(e)
            if '429' in err_str and attempt < MAX_RETRIES - 1:
                wait_time = RETRY_BASE_WAIT * (2 ** attempt)  # 15, 30, 60, 120 seconds
                print(f"  [RATE LIMIT] row {sheet_row_idx}, attempt {attempt+1}/{MAX_RETRIES}, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                return {"error": f"AI call failed: {e}"}
    if content is None:
        return {"error": "AI call failed: max retries exceeded"}

    # If Comment is missing from the response, retry once with a more explicit prompt
    if not parse_field(content, "Comment"):
        explicit_prompt = prompt + "\n\nIMPORTANT: You MUST fill in the Comment field with a complete English sentence describing what you see in the image. Do NOT leave it blank or write Unknown."
        try:
            response2 = client.chat.completions.create(
                model=MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                        {"type": "text", "text": explicit_prompt}
                    ]
                }],
                max_tokens=400
            )
            content2 = response2.choices[0].message.content
            if parse_field(content2, "Comment"):
                content = content2  # Use the retry response if it has a Comment
        except Exception:
            pass  # Keep original content if retry fails

    # Parse and map fields based on asset group
    uid = extract_unique_id(filename)
    result = {"_asset_group": asset_group, "_url_type": url_type}

    if asset_group == "Furniture":
        mood    = parse_field(content, "Mood") or "Furniture"
        writer  = parse_field(content, "Writer")
        album   = parse_field(content, "Album")
        loc     = parse_field(content, "Location")
        mat     = parse_field(content, "Material")
        style   = parse_field(content, "Style")
        shape   = parse_field(content, "Shape")
        color   = parse_field(content, "Color")
        author  = parse_field(content, "Author")
        tags    = parse_field(content, "Tags")
        comment = parse_field(content, "Comment")

        if writer: writer = fix_brand(writer)
        if tags:   tags = ",".join(t.strip()[0].upper()+t.strip()[1:] for t in tags.split(",") if t.strip())

        from_id = f"{mood}{album if album else uid}"
        to_val  = "".join(p for p in [filename,"Furniture",mood,writer,album,loc,mat,style,shape,color,tags,comment] if p)

        result.update({"Mood":mood,"Writer":writer,"Album":album,"People":loc,"Period":mat,
                       "Artist":style,"Company":shape,"Genre":color,"Author":author,
                       "Tags":tags,"Comment":comment,"From":from_id,"To":to_val,"Manager":"Furniture"})

    elif asset_group == "Fixture":
        mood    = parse_field(content, "Mood") or "Fixture"
        writer  = parse_field(content, "Writer")
        album   = parse_field(content, "Album")
        loc     = parse_field(content, "Location")
        mat     = parse_field(content, "Material")
        style   = parse_field(content, "Style")
        shape   = parse_field(content, "Shape")
        color   = parse_field(content, "Color")
        author  = parse_field(content, "Author")
        tags    = parse_field(content, "Tags")
        comment = parse_field(content, "Comment")

        if writer: writer = fix_brand(writer)
        if tags:   tags = ",".join(t.strip()[0].upper()+t.strip()[1:] for t in tags.split(",") if t.strip())

        # Preserve existing Mood if it was a useful subcategory (People migration)
        orig_people = get_row_value(row, "People")
        orig_mood   = get_row_value(row, "Mood")
        if orig_people and orig_mood in ("", "Filename", "Unknown"):
            mood = to_pascal(orig_people)

        from_id = f"{mood}{album if album else uid}"
        to_val  = "".join(p for p in [filename,"Fixture",mood,writer,album,loc,mat,style,shape,color,tags,comment] if p)

        result.update({"Mood":mood,"Writer":writer,"Album":album,"People":loc,"Period":mat,
                       "Artist":style,"Company":shape,"Genre":color,"Author":author,
                       "Tags":tags,"Comment":comment,"From":from_id,"To":to_val,"Manager":"Fixture"})

    elif asset_group == "Vegetation":
        plant_type  = parse_field(content, "PlantType") or "Vegetation"
        latin       = parse_field(content, "LatinName")
        common      = parse_field(content, "CommonName")
        loc         = parse_field(content, "Location")
        season      = parse_field(content, "Season")
        style       = parse_field(content, "Style")
        color       = parse_field(content, "Color")
        form        = parse_field(content, "Form")
        height      = parse_field(content, "Height")
        tags        = parse_field(content, "Tags")
        comment     = parse_field(content, "Comment")

        from_id = f"{plant_type}{latin if latin else ''}{uid}"
        to_val  = "".join(p for p in [filename,"Vegetation",plant_type,latin,common,loc,season,style,color,form,height,tags,comment] if p)

        result.update({"Mood":plant_type,"Writer":latin,"Album":common,"People":loc,"Period":season,
                       "Artist":style,"Genre":color,"Company":form,"Author":height,
                       "Tags":tags,"Comment":comment,"From":from_id,"To":to_val,"Manager":"Vegetation"})

    elif asset_group == "Material":
        mat_name = parse_field(content, "MaterialName") or "Material"
        mat_cat  = parse_field(content, "MaterialCategory") or "Material"
        surface  = parse_field(content, "Surface")
        color    = parse_field(content, "Color")
        pattern  = parse_field(content, "Pattern")
        tags     = parse_field(content, "Tags")
        comment  = parse_field(content, "Comment")

        from_id = f"{mat_cat}{color}{surface}{uid}"
        to_val  = "".join(p for p in [filename,"Material",mat_name,mat_cat,surface,color,pattern,tags,comment] if p)

        result.update({"Mood":mat_name,"Period":mat_cat,"Artist":surface,"Genre":color,
                       "Company":pattern,"Tags":tags,"Comment":comment,
                       "Writer":"","Album":"","People":"","Author":"",
                       "From":from_id,"To":to_val,"Manager":"Material"})

    elif asset_group == "People":
        gender    = parse_field(content, "Gender")
        ethnicity = parse_field(content, "Ethnicity")
        age_group = parse_field(content, "AgeGroup")
        pose      = parse_field(content, "Pose")
        clothing  = parse_field(content, "Clothing")
        color     = parse_field(content, "Color")
        loc       = parse_field(content, "Location")
        tags      = parse_field(content, "Tags")
        comment   = parse_field(content, "Comment")

        # Decode existing code hints from filename prefix (AXYZ naming convention)
        # Pattern: {ethnicity_code}{gender_code}{number}...
        # e.g. 'cman' = Chinese Male, 'bwom' = Black Female, 'arma' = Arab Male
        existing_code = get_row_value(row, "Mood").lower()
        if existing_code:
            # Gender decoding
            if 'man' in existing_code or existing_code[1:3] == 'ma': gender = 'Male'
            if 'wom' in existing_code or existing_code[1:3] == 'wo': gender = 'Female'
            if 'boy' in existing_code or existing_code[1:3] == 'bo': gender = 'Male'; age_group = 'Child'
            if 'gir' in existing_code or existing_code[1:3] == 'gi': gender = 'Female'; age_group = 'Child'
            if 'cou' in existing_code: gender = 'Mixed'; age_group = 'Couple'
            if 'fam' in existing_code: gender = 'Mixed'; age_group = 'Family'
            # Ethnicity decoding
            if existing_code.startswith('c') and not existing_code.startswith('ca'):
                ethnicity = 'Chinese'
            elif existing_code.startswith('b'): ethnicity = 'Black'
            elif existing_code.startswith('e'): ethnicity = 'European'
            elif existing_code.startswith('ar'): ethnicity = 'Arab'
            elif existing_code.startswith('su') or existing_code.startswith('sp') or existing_code.startswith('sf'):
                ethnicity = 'SouthAsian'
            elif existing_code.startswith('s') and not existing_code.startswith('sh'):
                ethnicity = 'SouthAsian'
            elif existing_code.startswith('w'): ethnicity = 'White'
            elif existing_code.startswith('mu'): ethnicity = 'Mixed'

        from_id = f"{ethnicity}{gender}{age_group}{uid}"
        to_val  = "".join(p for p in [filename,"People",gender,ethnicity,age_group,pose,clothing,color,loc,tags,comment] if p)

        result.update({"Author":gender,"Writer":ethnicity,"Album":age_group,"Artist":pose,
                       "Period":clothing,"Genre":color,"People":loc,
                       "Tags":tags,"Comment":comment,"From":from_id,"To":to_val,"Manager":"People"})

    elif asset_group == "FurnitureLike":
        subcat   = parse_field(content, "Subcategory") or "Object"
        brand    = parse_field(content, "Brand")
        prod     = parse_field(content, "ProductName")
        loc      = parse_field(content, "Location")
        mat      = parse_field(content, "Material")
        style    = parse_field(content, "Style")
        color    = parse_field(content, "Color")
        shape    = parse_field(content, "Shape")
        tags     = parse_field(content, "Tags")
        comment  = parse_field(content, "Comment")

        from_id = f"{subcat}{prod if prod else uid}"
        to_val  = "".join(p for p in [filename,url_type,subcat,brand,prod,loc,mat,style,color,shape,tags,comment] if p)

        result.update({"Mood":subcat,"Writer":brand,"Album":prod,"People":loc,"Period":mat,
                       "Artist":style,"Genre":color,"Company":shape,
                       "Tags":tags,"Comment":comment,"From":from_id,"To":to_val,"Manager":"FurnitureLike"})

    elif asset_group == "Buildings":
        subcat  = parse_field(content, "Subcategory") or "BuildingElement"
        mat     = parse_field(content, "Material")
        style   = parse_field(content, "Style")
        form    = parse_field(content, "Form")
        tags    = parse_field(content, "Tags")
        comment = parse_field(content, "Comment")
        # NOTE: Color intentionally skipped for Buildings (diagram backgrounds interfere)

        from_id = f"{subcat}{uid}"
        to_val  = "".join(p for p in [filename,"Buildings",subcat,mat,style,form,tags,comment] if p)

        result.update({"Mood":subcat,"Period":mat,"Artist":style,"Company":form,
                       "Tags":tags,"Comment":comment,
                       "Writer":"","Album":"","People":"","Genre":"","Author":"",
                       "From":from_id,"To":to_val,"Manager":"Buildings"})

    elif asset_group == "Layouts":
        l_type  = parse_field(content, "LayoutType") or "Layout"
        room    = parse_field(content, "RoomType")
        size    = parse_field(content, "ApproxSize")
        shape   = parse_field(content, "Shape")
        tags    = parse_field(content, "Tags")
        comment = parse_field(content, "Comment")

        from_id = f"{l_type}{uid}"
        to_val  = "".join(p for p in [filename,"Layouts",l_type,room,size,shape,tags,comment] if p)

        result.update({"Mood":l_type,"People":room,"Writer":size,"Period":shape,
                       "Tags":tags,"Comment":comment,
                       "Album":"","Artist":"","Company":"","Author":"","Genre":"",
                       "From":from_id,"To":to_val,"Manager":"Layouts"})

    return result

# ---------------------------------------------------------------------------
# SHEET WRITER
# ---------------------------------------------------------------------------
def write_batch_to_sheet(batch_updates: list, dry_run: bool = False):
    """Write a list of (sheet_row_idx, col_name, value) tuples to the sheet.
    sheet_row_idx is 1-indexed (row 1 = header, row 2 = first data row).
    """
    if not batch_updates:
        return

    # Build batchUpdate data: list of ValueRange objects
    value_ranges = []
    for (row_idx, col_name, value) in batch_updates:
        col_letter = chr(ord('A') + COL[col_name])
        cell_ref = f"{SHEET_NAME}!{col_letter}{row_idx}"
        value_ranges.append({
            "range": cell_ref,
            "values": [[str(value) if value is not None else ""]]
        })

    if dry_run:
        print(f"  [DRY RUN] Would write {len(value_ranges)} cells")
        return

    params = {
        "spreadsheetId": SPREADSHEET_ID,
        "range": f"{SHEET_NAME}!A1",  # placeholder, overridden by data
    }
    body = {
        "valueInputOption": "RAW",
        "data": value_ranges
    }

    result = subprocess.run(
        ["gws", "sheets", "spreadsheets", "values", "batchUpdate",
         "--params", json.dumps({"spreadsheetId": SPREADSHEET_ID}),
         "--json", json.dumps(body)],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"  [SHEET WRITE ERROR] {result.stderr[:200]}")
    else:
        resp = json.loads(result.stdout)
        total_updated = resp.get("totalUpdatedCells", "?")
        print(f"  [SHEET] Wrote {total_updated} cells to sheet")

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="AI enrichment pipeline for CurrentDB")
    parser.add_argument("--test", type=int, default=None, metavar="N",
                        help="Process N randomly sampled rows (default: 100 for test mode)")
    parser.add_argument("--types", type=str, default=None,
                        help="Comma-separated URL types to process (e.g. Furniture,Vegetation)")
    parser.add_argument("--start-row", type=int, default=None,
                        help="Resume from sheet row number (1-indexed, excluding header)")
    parser.add_argument("--full", action="store_true",
                        help="Run full production batch")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and plan without calling AI or writing to sheet")
    parser.add_argument("--retry-file", type=str, default=None,
                        help="File containing sheet row numbers to retry (one per line)")
    args = parser.parse_args()

    # Retry mode: process only specific rows
    if args.retry_file:
        print("=" * 70)
        print(f"  CurrentDB AI Enrichment Pipeline - RETRY MODE")
        print("=" * 70)
        with open(args.retry_file) as f:
            retry_rows = sorted(int(l.strip()) for l in f if l.strip())
        print(f"Rows to retry: {len(retry_rows)}")

        with open(DB_ROWS_CACHE) as f:
            all_rows = json.load(f)
        headers_r = all_rows[0]
        data_rows_r = all_rows[1:]

        sample = []
        for sheet_row in retry_rows:
            data_idx = sheet_row - 2
            if 0 <= data_idx < len(data_rows_r):
                row = data_rows_r[data_idx]
                if len(row) > COL["URL"] and get_asset_group(get_row_value(row, "URL")) is not None:
                    sample.append((data_idx, row))

        print(f"Processable retry rows: {len(sample)}")
        tmp_dir = tempfile.mkdtemp(prefix="enrich_retry_")
        print(f"Temp directory: {tmp_dir}")
        print(f"Workers: {MAX_WORKERS}, Batch write size: {BATCH_WRITE_SZ}")
        print("Starting retry processing...\n")

        total_r = len(sample)
        processed_r = 0
        errors_r = 0
        pending_writes_r = []

        def process_one_retry(item):
            data_idx, row = item
            sheet_row = data_idx + 2
            return sheet_row, analyze_row(sheet_row, row, tmp_dir)

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures_r = {executor.submit(process_one_retry, item): item for item in sample}
            for future in as_completed(futures_r):
                item = futures_r[future]
                data_idx, row = item
                sheet_row = data_idx + 2
                try:
                    _, result = future.result()
                except Exception as e:
                    result = {"error": str(e)}
                processed_r += 1
                filename = get_row_value(row, "Filename") if len(row) > COL["Filename"] else "?"
                if "error" in result:
                    errors_r += 1
                    print(f"  [{processed_r:4d}/{total_r}] ERROR  row {sheet_row:6d}: {result['error'][:60]}")
                else:
                    from_val = result.get("From", "?")
                    group    = result.get("_asset_group", "?")
                    print(f"  [{processed_r:4d}/{total_r}] OK     row {sheet_row:6d} [{group:12s}]: {os.path.basename(filename)} -> {from_val[:40]}")
                    for col_name in WRITE_COLS:
                        if col_name in result:
                            val = result[col_name]
                            if val is not None:
                                pending_writes_r.append((sheet_row, col_name, val))
                if len(pending_writes_r) >= BATCH_WRITE_SZ * len(WRITE_COLS):
                    with _lock:
                        write_batch_to_sheet(pending_writes_r)
                        pending_writes_r.clear()

        if pending_writes_r:
            write_batch_to_sheet(pending_writes_r)
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f"\n{'='*70}")
        print(f"  RETRY DONE: {processed_r} rows processed, {errors_r} errors")
        print(f"{'='*70}")
        return

    # Default: test mode with 100 rows
    if not args.full and args.test is None:
        args.test = 100

    print("=" * 70)
    print("  CurrentDB AI Enrichment Pipeline (Google Drive Edition)")
    print("=" * 70)

    # Load DB rows
    print(f"\nLoading database from {DB_ROWS_CACHE}...")
    with open(DB_ROWS_CACHE) as f:
        all_rows = json.load(f)

    headers = all_rows[0]
    data_rows = all_rows[1:]  # 0-indexed within data_rows; sheet row = idx+2
    print(f"Total data rows: {len(data_rows)}")

    # Filter by type if requested
    if args.types:
        target_types = [t.strip().lower() for t in args.types.split(",")]
        data_rows_filtered = [(i, r) for i, r in enumerate(data_rows)
                              if len(r) > COL["URL"] and r[COL["URL"]].lower() in target_types]
    else:
        # Only process rows with known asset groups
        data_rows_filtered = [(i, r) for i, r in enumerate(data_rows)
                              if len(r) > COL["URL"] and get_asset_group(r[COL["URL"]]) is not None]

    print(f"Rows with processable asset types: {len(data_rows_filtered)}")

    # Apply start-row filter
    if args.start_row:
        data_rows_filtered = [(i, r) for i, r in data_rows_filtered if i + 2 >= args.start_row]
        print(f"After start-row filter: {len(data_rows_filtered)}")

    # Sample for test mode
    if args.test:
        random.seed(42)
        sample = random.sample(data_rows_filtered, min(args.test, len(data_rows_filtered)))
        sample.sort(key=lambda x: x[0])  # Sort by original row order
        print(f"\nTest mode: randomly sampled {len(sample)} rows")

        # Show distribution
        from collections import Counter
        type_dist = Counter(r[COL["URL"]] for _, r in sample if len(r) > COL["URL"])
        print("Sample distribution by type:")
        for t, c in sorted(type_dist.items(), key=lambda x: -x[1]):
            print(f"  {t:20s}: {c}")
    else:
        sample = data_rows_filtered
        print(f"\nFull run: processing {len(sample)} rows")

    if args.dry_run:
        print("\n[DRY RUN MODE] No AI calls or sheet writes will be made.")

    # Create temp directory for image downloads
    tmp_dir = tempfile.mkdtemp(prefix="enrich_")
    print(f"\nTemp directory: {tmp_dir}")
    print(f"Workers: {MAX_WORKERS}, Batch write size: {BATCH_WRITE_SZ}")
    print("\nStarting processing...\n")

    # Track results
    total = len(sample)
    processed = 0
    errors = 0
    pending_writes = []
    results_log = []

    def process_one(item):
        data_idx, row = item
        sheet_row = data_idx + 2  # +1 for header, +1 for 1-indexing
        if args.dry_run:
            return sheet_row, {"_dry_run": True, "_asset_group": get_asset_group(get_row_value(row, "URL") if len(row) > COL["URL"] else "")}
        return sheet_row, analyze_row(sheet_row, row, tmp_dir)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_one, item): item for item in sample}

        for future in as_completed(futures):
            item = futures[future]
            data_idx, row = item
            sheet_row = data_idx + 2

            try:
                _, result = future.result()
            except Exception as e:
                result = {"error": str(e)}

            processed += 1
            filename = get_row_value(row, "Filename") if len(row) > COL["Filename"] else "?"

            if "error" in result:
                errors += 1
                print(f"  [{processed:4d}/{total}] ERROR  row {sheet_row:6d}: {result['error'][:60]}")
            else:
                from_val = result.get("From", "?")
                group    = result.get("_asset_group", "?")
                print(f"  [{processed:4d}/{total}] OK     row {sheet_row:6d} [{group:12s}]: {os.path.basename(filename)} -> {from_val[:40]}")

                # Queue writes for all non-empty result fields
                for col_name in WRITE_COLS:
                    if col_name in result:
                        val = result[col_name]
                        if val is not None:  # Write even empty strings to clear old values
                            pending_writes.append((sheet_row, col_name, val))

                results_log.append({
                    "sheet_row": sheet_row,
                    "filename": filename,
                    "asset_group": group,
                    "from": from_val,
                    "result": {k: v for k, v in result.items() if not k.startswith("_")}
                })

            # Flush writes in batches
            if len(pending_writes) >= BATCH_WRITE_SZ * len(WRITE_COLS):
                with _lock:
                    write_batch_to_sheet(pending_writes, dry_run=args.dry_run)
                    pending_writes.clear()

    # Final flush
    if pending_writes:
        write_batch_to_sheet(pending_writes, dry_run=args.dry_run)
        pending_writes.clear()

    # Save results log
    log_path = "/home/ubuntu/enrich_results.json"
    with open(log_path, "w") as f:
        json.dump(results_log, f, indent=2)

    # Cleanup temp dir
    try:
        import shutil
        shutil.rmtree(tmp_dir)
    except Exception:
        pass

    print(f"\n{'='*70}")
    print(f"  DONE: {processed} rows processed, {errors} errors")
    print(f"  Results log: {log_path}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# RETRY MODE: process only specific row numbers from a file
# ---------------------------------------------------------------------------
def run_retry(retry_file: str):
    """Process only rows listed in retry_file."""
    with open(retry_file) as f:
        retry_rows = sorted(int(l.strip()) for l in f if l.strip())

    print("=" * 70)
    print(f"  RETRY MODE: {len(retry_rows)} rows to retry")
    print("=" * 70)

    with open(DB_CACHE) as f:
        data = json.load(f)
    headers = data[0]
    all_rows = data[1:]

    fn_idx    = headers.index('Filename')
    type_idx  = headers.index('Type')

    tasks = []
    for sheet_row in retry_rows:
        data_idx = sheet_row - 2
        if data_idx < 0 or data_idx >= len(all_rows):
            continue
        row = all_rows[data_idx]
        asset_type = row[type_idx].strip() if type_idx < len(row) else ""
        if asset_type not in PROCESSABLE_TYPES:
            continue
        tasks.append((sheet_row, row, headers))

    print(f"Processable retry tasks: {len(tasks)}")

    tmp_dir = tempfile.mkdtemp(prefix="enrich_retry_")
    print(f"Temp directory: {tmp_dir}")
    print(f"Workers: {MAX_WORKERS}, Batch write size: {BATCH_SIZE}")
    print("Starting retry processing...")

    pending_writes = []
    ok_count = 0
    err_count = 0
    total = len(tasks)

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_task = {
            executor.submit(process_row, sheet_row, row, headers, tmp_dir): (sheet_row, row)
            for sheet_row, row, headers in tasks
        }
        for i, future in enumerate(concurrent.futures.as_completed(future_to_task), 1):
            sheet_row, row = future_to_task[future]
            try:
                result = future.result()
                if result:
                    pending_writes.append(result)
                    ok_count += 1
                    fn = row[fn_idx] if fn_idx < len(row) else ""
                    asset_type = row[headers.index('Type')].strip() if 'Type' in headers else ""
                    from_id = result.get('from_id', '')
                    print(f"  [{i:5d}/{total}] OK     row {sheet_row:6d} [{asset_type:12s}]: {os.path.basename(fn)} -> {from_id[:40]}")
                else:
                    err_count += 1
                    fn = row[fn_idx] if fn_idx < len(row) else ""
                    print(f"  [{i:5d}/{total}] SKIP   row {sheet_row:6d}: no result")
            except Exception as e:
                err_count += 1
                print(f"  [{i:5d}/{total}] ERROR  row {sheet_row:6d}: {e}")

            if len(pending_writes) >= BATCH_SIZE:
                write_batch_to_sheet(pending_writes)
                pending_writes = []

    if pending_writes:
        write_batch_to_sheet(pending_writes)

    shutil.rmtree(tmp_dir, ignore_errors=True)
    print("=" * 70)
    print(f"  RETRY DONE: {ok_count} OK, {err_count} skipped/failed")
    print("=" * 70)
