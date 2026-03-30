# drive-image-processor

A local Python pipeline for enriching a 3D asset library with AI-generated metadata, stored in Google Sheets and searchable via Everything Search.

## Repository Structure

```
drive-image-processor/
├── pipeline/               # Core enrichment and processing scripts
│   ├── enrich_gdrive.py    # Main enrichment script (all 8 asset types)
│   ├── process_folder.py   # Single-folder processor (original)
│   └── requirements.txt    # Python dependencies
│
├── schedule-matcher/       # (Planned) Schedule-to-asset matching automation
│
├── tools/                  # Utility and maintenance scripts
│   ├── compare_apis.py     # API benchmark: Gemini vs Cloud Vision vs Vertex AI
│   ├── rebuild_drive_index.py
│   ├── fix_drive_filenames.py
│   ├── scan_drive_all_files.py
│   └── add_new_rows_to_sheet.py
│
├── knowledge/              # Architecture decisions and reference documents
│   ├── 3D_Asset_Workflow_Architecture.md
│   └── Naming_Convention.md
│
├── archive/                # Obsolete scripts kept for reference
│   ├── search_database.py  # Vertex AI Search era (abandoned)
│   └── sync_to_search.py   # Vertex AI Search era (abandoned)
│
└── scratch/                # Unorganised exploratory scripts
```

## Setup

Set the following environment variables before running any script:

```bash
# Windows (PowerShell)
$env:GEMINI_API_KEY="<your-gemini-api-key>"
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\service-account.json"
```

Install dependencies:

```bash
pip install -r pipeline/requirements.txt
```

## Key Scripts

**`pipeline/enrich_gdrive.py`** — The main enrichment script. Reads the `CurrentDB` Google Sheet, finds rows with images but missing metadata, sends each image to Gemini 2.5 Flash, and writes structured metadata back to the sheet. Supports 8 asset categories: Furniture, Fixture, Vegetation, Material, People, Buildings, Layouts, and FurnitureLike objects.

**`pipeline/process_folder.py`** — Processes a single Google Drive folder from scratch, creating a new sheet tab with all extracted metadata.

## Naming Conventions

See `knowledge/Naming_Convention.md` for the full naming rules covering scripts, folders, database values, and Google Drive structure.
