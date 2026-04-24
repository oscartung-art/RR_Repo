# Schedule PDF Workflow Reference

Quick reference for the two-step schedule extraction and enrichment workflow.

## Overview

**Old workflow (legacy):** PDF → parse + extract images + AI cleanup → write EFU (single step, complex)

**New workflow (two-step):**
  1. PDF → extract metadata to JSON + optionally extract images (flexible, editable)
  2. PDF → extract images (if not already extracted) + enrich with JSON → write EFU (decoupled, simple)

## Step-by-Step Guide

### Step 1: Extract Metadata to JSON (and optionally images)

**Preview first:**
```powershell
cd D:\rr_repo
.\.venv\Scripts\python.exe tools/extract_schedule_json.py --dry-run "path/to/schedule.pdf"
```

**Review output:**
- Project name, Client name, Total entries
- Preview table showing extracted metadata
- First entry in full detail
- Image extraction support status

**Write JSON only:**
```powershell
cd D:\rr_repo
.\.venv\Scripts\python.exe tools/extract_schedule_json.py --yes "path/to/schedule.pdf"
```

**Write JSON + extract images:**
```powershell
cd D:\rr_repo
.\.venv\Scripts\python.exe tools/extract_schedule_json.py --yes --extract-images "path/to/schedule.pdf"
```

**Output:**
- `schedule.json` in same directory as PDF
- `<CODE>.jpg` files in same directory (if --extract-images used)

### Step 2a: Extract Images by Code (if not already extracted)

If you only extracted JSON in Step 1, use this to extract images:

**Via clipboard watcher:**
```
"G:\DB\schedules\material_spec.pdf" create:
```

**What it does:**
- Extracts largest image from each page
- Names files by code (PL-01.jpg, PL-02.jpg, etc.)
- Saves to same directory as PDF
- No EFU creation yet

### Step 2b: Enrich Images with JSON

**Edit JSON if needed** (optional):
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
  }
}
```

**Enrich via clipboard watcher:**
```
"G:\DB\schedules\extracted\" "G:\DB\schedules\material_spec.json" enrich:
```

**What it does:**
- Reads JSON metadata
- Matches images by code name
- Creates/updates `.metadata.efu`
- Preserves existing rows

## Advantages of Two-Step Workflow

✅ **Flexible**: Edit JSON with any text editor before enrichment
✅ **Simple**: Image extraction is deterministic (largest image per page)
✅ **Decoupled**: Can extract images and metadata independently
✅ **Reviewable**: JSON is human-readable, easy to verify
✅ **Reusable**: Same JSON can enrich multiple image sets
✅ **AI-Enhanced**: AI cleanup runs during JSON generation, not at enrichment time
✅ **Image-Smart**: Skips headers, icons, logos when extracting product images

## Common Scenarios

### Single PDF, One Pass (JSON + Images)
```bash
# 1. Extract everything in one pass
python tools/extract_schedule_json.py --yes --extract-images "spec.pdf"

# 2. Review JSON if needed, then enrich
# Copy: "folder\" "metadata.json" enrich:
```

### Single PDF, Two Pass (Preview → Extract)
```bash
# 1. Preview extraction
python tools/extract_schedule_json.py --dry-run "spec.pdf"

# 2. Extract metadata and images
python tools/extract_schedule_json.py --yes --extract-images "spec.pdf"

# 3. Review JSON if needed, then enrich
# Copy: "folder\" "metadata.json" enrich:
```

### Review and Edit Before Enrichment
```bash
# 1. Generate JSON (no images yet)
python tools/extract_schedule_json.py --yes "spec.pdf"

# 2. Open spec.json in editor, fix any extraction errors

# 3. Extract images (either via create: command or via --extract-images flag)
python tools/extract_schedule_json.py --yes --extract-images "spec.pdf"

# 4. Enrich
# Copy: "folder\" "metadata.json" enrich:
```

### Re-enrich with Updated JSON
```bash
# Already extracted images, just update JSON and re-enrich
# (Edit spec.json)
# Copy: "folder\" "metadata.json" enrich:
```

### Multiple PDFs, Same Project
```bash
# Extract all schedules to JSON and images first
python tools/extract_schedule_json.py --yes --extract-images "lighting.pdf"
python tools/extract_schedule_json.py --yes --extract-images "furniture.pdf"
python tools/extract_schedule_json.py --yes --extract-images "material.pdf"

# Review/edit JSONs as needed

# Enrich one by one
# Copy: "lighting_folder\" "lighting.json" enrich:
# Copy: "furniture_folder\" "furniture.json" enrich:
# Copy: "material_folder\" "material.json" enrich:
```

## Troubleshooting

### No images extracted
- Check PDF has valid page images (not just text)
- Verify CODE: field exists on each page
- Check clipboard watcher is running (if using create: command)
- Ensure pymupdf (fitz) is installed (if using --extract-images flag)

### JSON has wrong data
- Review AI cleanup output
- Manually edit JSON before enrichment
- Check PDF format matches expected structure

### Enrichment skips files
- Verify image filenames match JSON keys exactly
- Check file exists in specified folder
- Look for case sensitivity issues (PL-01.jpg vs pl-01.jpg)

### AI cleanup not working
- Check OpenRouter API key is set
- Verify internet connection
- Review extraction output for AI response

## Files and Locations

**Skill definition:** `.github/skills/extract-schedule-json/SKILL.md`
**Documentation:** `.github/skills/extract-schedule-json/README.md`
**Script:** `tools/extract_schedule_json.py`
**Watcher logic:** `tools/watcher.py`
**Extraction logic:** `tools/ingest_schedule.py`

## Related Documentation

- [AGENTS.md](../AGENTS.md) - Agent guidelines and commands
- [manual/everything_columnmapping.md](../manual/everything_columnmapping.md) - EFU column definitions
- [README.md](../README.md) - Repository overview
