---
name: ingest-schedule
description: Ingests any interior design schedule (material, sanitary, furniture, lighting, etc.) from a PDF and writes/appends to a .metadata.efu file with extracted product thumbnails. Use when the user pastes a PDF path and wants to convert a spec schedule.
allowed-tools: shell, powershell
---

## ingest-schedule

Convert any design schedule PDF into a `.metadata.efu` file with canonical EFU column names.

### What it does

Parses a PDF where each page (after a title/cover page) contains one schedule entry
in a table. Works for material, sanitary, furniture, lighting, and other schedule types.

Maps extracted fields to EFU columns:

| Schedule Field | EFU Column | Semantic Meaning |
|---|---|---|
| `<SubjectLeaf>_<Brand><ModelRef>` | `Filename` | Filename (synthetic identifier) |
| Item / Subcategory | `custom_property_0` | Subject (`AssetType/TitleCaseItem` e.g. Fixture/WaterCloset) |
| Model spec (after brand) | `custom_property_1` | Model name |
| Brand (from quoted model prefix) | `custom_property_2` | Brand/Designer |
| — | `custom_property_3` | Style/era (empty in schedule extraction) |
| Color + Finish | `custom_property_4` | Color/Material/Surface finish |
| Location | `custom_property_5` | Usage context/Location (room/area) |
| — | `custom_property_6` | Shape/Form (empty in schedule extraction) |
| Dimension | `custom_property_7` | Dimensions/Size |
| Code | `custom_property_8` | Reference code |
| — | `custom_property_9` | Reserved (unused)

### How to invoke — ALWAYS show final enriched table first

**Step 1 — Show Final Enriched Table (always run first):**

Use the helper to show the final enriched table (it will prompt for output folder):

```
cd D:\rr_repo && .\.venv\Scripts\python.exe "tools/display_schedule_preview.py" "<PDF_PATH>"
```

This will display:
- Project name, Client name, Album folder name, Total entries count
- Formatted markdown table with columns: Code, Subject, Title, Finish, Color, Size, Location
- All enriched rows for final verification before writing EFU

Then ask: **"Final enriched table looks good — write the file?"**

**Step 2 — Write (only after user confirms):**

```
cd D:\rr_repo && .\.venv\Scripts\python.exe "tools/ingest_schedule.py" "<PDF_PATH>"
```

**Optional flags:**
- `--out "<DIR>"` — set output directory directly (skips prompt)
- `--type fixture|furniture|material|object` — override asset root type (auto-detected from filename if omitted)
- `--no-images` — skip product image extraction (faster for testing)

### After writing

Report to the user:
- Project name, client, number of entries written
- Where the `.metadata.efu` was written (or appended)
- Any entries with missing fields (shown with `-`)

### Notes

- Skips the first page (title/cover) automatically
- Dry-run/CSV table is the final enriched result (AI enabled by default)
- Use `--skip-ai` only when you want a faster diagnostic table
- If `--out` is omitted, the script prompts for output folder path and uses that folder name as `Album`
- Code pattern is flexible — matches `MATERIAL CODE`, `FURNITURE CODE`, `SANITARY CODE`, etc.
- Subject is built as `AssetType/TitleCaseItem` (e.g. `Fixture/SensorBasinMixer`) — asset type auto-detected from PDF filename
- Brand is extracted from quoted prefix in Model field (e.g. `"AXOR" 38120140` → Company=AXOR, Title=38120140)
- Filename is `<SubjectLeaf>_<Brand><ModelRef>` (TitleCase, non-alphanumeric stripped)
- Uses `pdfplumber` (already installed in the repo venv)
