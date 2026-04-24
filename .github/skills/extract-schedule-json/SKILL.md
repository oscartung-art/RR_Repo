---
name: extract-schedule-json
description: Analyzes interior design schedule PDF patterns using AI, extracts metadata to JSON, and extracts relevant product images while skipping useless content (headers, icons, logos). Generates structured JSON for enrichment.
allowed-tools: shell, powershell
---

## extract-schedule-json

Analyze schedule/catalogue PDF patterns using AI, extract metadata to JSON, and extract relevant product images.

### What it does

1. **AI Pattern Analysis**: Uses AI to identify schedule patterns:
   - Detects table structures
   - Finds common field patterns (Code, Item, Brand, etc.)
   - Handles various table layouts (2-col, 4-col, 7-col)

2. **Extracts Structured JSON Keyed by Code**:
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

3. **Extracts Relevant Images**:
   - Skips header logos and recurring images (appearing on >50% of pages)
   - Skips small icons/thin lines (<60px)
   - Extracts product images (largest relevant image per page)
   - Names images by code: `PL-01.jpg`, `PL-02.jpg`, etc.

4. **Saves Results**: JSON and images saved to same directory as PDF

### How to invoke

Always use the helper script and show preview first:

**Step 1 — Preview (always run first):**

```powershell
cd D:\rr_repo
.\.venv\Scripts\python.exe "tools/extract_schedule_json.py" --dry-run "<PDF_PATH>"
```

This displays:
- Project name, Client name, Total entries
- Preview table showing all extracted metadata
- JSON structure for first entry
- Page count and image extraction preview

Then ask: **"Preview looks good — extract metadata and images?"**

**Step 2 — Extract JSON and Images:**

```powershell
cd D:\rr_repo
.\.venv\Scripts\python.exe "tools/extract_schedule_json.py" --yes --extract-images "<PDF_PATH>"
```

Output: 
- `<PDF_BASENAME>.json` in same directory
- Extracted images: `<CODE>.jpg` files in same directory

### Image Extraction Logic

The AI-driven image extraction:
- **Skips useless content**: Headers, logos, icons, thin lines, repeating elements
- **Extracts product images**: Largest image per page that's not a header
- **Finds relevant images**: Uses page content to determine if an image is table-related
- **Handles multiple images**: Combines side-by-side product images

### Supported PDF Types

- **Material specifications** (tiles, stone, flooring, wall finishes)
- **Sanitary schedules** (bathroom fixtures, plumbing)
- **Furniture schedules** (seating, tables, storage)
- **Lighting schedules** (luminaires, lamps)
- **Hardware schedules** (doors, windows, ironmongery)
- **Catalogue-style schedules** with product images

### Error Handling

If extraction fails:
1. Check PDF has valid page structure (table with CODE: field)
2. Verify pdfplumber and dependencies installed (`pip install -r requirements.txt`)
3. Try opening PDF manually to check corruption
4. For image issues: Check if PDF has images (some PDFs are scanned text)

### Next Steps

After extraction:
1. Review/edit JSON file if needed
2. Enrich images with metadata using clipboard watcher: `"PDF_FOLDER" "<PDF_BASENAME>.json" enrich:`
3. The resulting `.metadata.efu` file is ready for asset ingestion
