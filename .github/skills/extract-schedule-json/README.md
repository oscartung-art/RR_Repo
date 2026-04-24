# Extract Schedule JSON Skill

Extracts metadata from interior design schedule PDFs into JSON format, and optionally extracts relevant product images while skipping useless content (headers, icons, logos).

## Purpose

This skill analyzes schedule/catalogue PDFs using AI to detect patterns, extract metadata, and extract relevant product images. It supports the two-step enrichment workflow:

1. **Extract metadata to JSON** - Parse PDF and generate JSON with all metadata
2. **[Optional] Extract images** - Extract product images while skipping useless content
3. **Enrich with JSON** - Use `"folder" "metadata.json" enrich:` to combine

## Features

- **AI Pattern Analysis**: Detects table structures and common field patterns
- Parses schedule PDFs with one item per page
- Extracts: Code, Subject, Brand, Model, Color, Location, Dimensions
- Uses AI cleanup to remove contact info and normalize fields
- Outputs JSON keyed by code name (e.g., `"PL-01": {...}`)
- Saves JSON in same directory as PDF
- **Image Extraction**: Extracts relevant product images, skipping:
  - Header images (recurring on >50% of pages)
  - Small icons/thin lines (<60px)
  - Logos and other useless content
- **Names images by code**: `<CODE>.jpg` for easy matching with JSON

## Usage

### Step 1: Preview (Dry Run)

Always preview first:

```powershell
cd D:\rr_repo
.\.venv\Scripts\python.exe "tools/extract_schedule_json.py" --dry-run "path/to/schedule.pdf"
```

Shows:
- Project, Client, Total entries
- Preview table of all entries
- Full detail of first entry
- Image extraction support status

### Step 2: Write JSON Only

After confirming preview:

```powershell
cd D:\rr_repo
.\.venv\Scripts\python.exe "tools/extract_schedule_json.py" --yes "path/to/schedule.pdf"
```

Creates: `schedule.json` in same directory

### Step 3: Write JSON + Extract Images

To extract both metadata and images:

```powershell
cd D:\rr_repo
.\.venv\Scripts\python.exe "tools/extract_schedule_json.py" --yes --extract-images "path/to/schedule.pdf"
```

Outputs:
- `schedule.json` - metadata file
- `<CODE>.jpg` - product images per code (e.g., `PL-01.jpg`, `PL-02.jpg`)

### Optional: Override Asset Type

If auto-detection is wrong:

```powershell
.\.venv\Scripts\python.exe "tools/extract_schedule_json.py" --yes --extract-images --asset-type=material "path/to/schedule.pdf"
```

## JSON Format

```json
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
  "PL-02": {
    ...
  }
}
```

## Next Steps After Extraction

1. **Review/Edit JSON** - Open in editor and fix any extraction errors
2. **Enrich** - Enrich images with JSON: `"folder" "metadata.json" enrich:`
   - If you used `--extract-images`, just run the enrich command on the same folder

## Example Workflow

### Single Command (JSON + Images)

```bash
# Extract metadata and images in one pass
python tools/extract_schedule_json.py --yes --extract-images "G:\DB\schedules\material_spec.pdf"

# Enrich images with JSON
# Copy: "G:\DB\schedules\" "G:\DB\schedules\material_spec.json" enrich:
```

### Two-Step Workflow (Preview First)

```bash
# 1. Preview extraction
python tools/extract_schedule_json.py --dry-run "G:\DB\schedules\material_spec.pdf"

# 2. Extract JSON and images
python tools/extract_schedule_json.py --yes --extract-images "G:\DB\schedules\material_spec.pdf"

# 3. Review JSON, then enrich
python -m json.tool "G:\DB\schedules\material_spec.json"
# Copy: "G:\DB\schedules\" "G:\DB\schedules\material_spec.json" enrich:
```

## AI Cleanup

The script automatically calls AI cleanup to:
- Remove redundant Subject text (e.g., "Fixture/WaterClosetCistern" → "Fixture/WaterCloset")
- Clean Color/finish to only color/finish names
- Remove contact info (emails, phones) from all fields
- Normalize location to room/area names only
- Ensure dimensions only contain size specs

## Error Handling

If extraction fails:
1. Check PDF has CODE: field on each page
2. Verify PDF isn't corrupted
3. Check OpenRouter API key is set for AI cleanup
4. Try manual extraction and JSON editing
5. For image issues: Ensure `pymupdf` is installed (`pip install pymupdf`)

## Dependencies

- Python 3.10+
- pdfplumber (PDF parsing)
- requests (for AI cleanup)
- pymupdf (fitz) (for image extraction)
- OpenRouter API key (optional but recommended)

## Supported PDF Types

- **Material specifications** (tiles, stone, flooring, wall finishes)
- **Sanitary schedules** (bathroom fixtures, plumbing)
- **Furniture schedules** (seating, tables, storage)
- **Lighting schedules** (luminaires, lamps)
- **Hardware schedules** (doors, windows, ironmongery)
- **Catalogue-style schedules** with product images
