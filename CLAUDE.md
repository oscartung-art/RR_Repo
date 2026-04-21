```
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
```

## RR Repo Overview

This is the operational workspace for Real Rendering automation. It combines:
- Project management (markdown files per project)
- Asset library tooling (indexing, semantic search, rating/tag sidecars)
- AI-powered asset ingestion and metadata enrichment

## Setup

### Environment
- OS: Windows
- Shell: PowerShell
- Python venv already set up: `.venv\Scripts\python.exe`

### Activate Environment
```powershell
cd D:\rr_repo
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt  # if dependencies need to be updated
```

## Core Commands

### Syntax Check
```powershell
python -m py_compile <file.py>
```

### Asset Ingestion (Primary Entry Point)
**Dry Run (Always First!):**
```powershell
python tools/ingest_asset.py --dry-run --asset-type=furniture "IMAGE_PATH" "ARCHIVE_PATH"
```
**Apply:**
```powershell
python tools/ingest_asset.py --yes --asset-type=furniture "IMAGE_PATH" "ARCHIVE_PATH"
```

### Tests
**Run All Tests:**
```powershell
python -m pytest  # if pytest is installed
# OR run individual tests directly
python tests/test_live_vision_path.py
python tests/test_sculpture_path.py
python tests/test_all_categories.py
```

### Keyword Audit
```powershell
python tools/audit_keywords.py
```

### EFU Column Mapping
Check canonical metadata column definitions: `manual/everything_columnmapping.md`

## High-Level Architecture

### Entry Points
1. **`tools/`**: Operational automation and asset ingestion (canonical path: `tools/ingest_asset.py`)
2. **`scripts/`**: Indexing, vector search (CLIP), semantic search, and tagging
3. **`Shared/`**: Shared configuration and helpers
4. **`projects/`**: Per-project markdown records (freeform, no schema)
5. **`manual/`**: Authoritative metadata conventions (critical: `everything_columnmapping.md`)
6. **`Database/`**: Local EFU metadata store
7. **`tests/`**: Diagnostic/regression scripts

### Data Flow
```
Ingestion (tools/ingest_asset.py) 
  → Metadata Enrichment (AI) 
  → Write .metadata.efu sidecar 
  → Update indexes 
  → Build semantic search vectors (scripts/) 
  → Queries
```

### GitHub Copilot Skills (Custom)
Located in `.github/skills/`:
1. **ingest-asset**: Runs `tools/ingest_asset.py` for asset ingestion
2. **ingest-schedule**: Converts design schedule PDFs to EFU files
3. **edit-efu-metadata**: Updates fields in .metadata.efu files
4. **move-delete-assets**: Moves/deletes assets and syncs EFU

### Key Conventions
- **EFU Format**: Column names from `everything_columnmapping.md` are canonical
- **Subject Classification**: AI-determined as `AssetType/<AI subject>`
- **Dry Run First**: Always preview changes before applying
- **Windows Paths**: Assume Windows-style paths (e.g., `G:\DB\`)
- **Experiments**: Use `scratch/` directory
- **Archive**: Move superseded files to `archive/` (don't delete blindly)
- **Secrets**: Never commit API keys/tokens - use environment variables

## Important Files

1. **`manual/everything_columnmapping.md`**: Defines all metadata fields for assets
2. **`AGENTS.md`**: Agent guidelines and recurring commands
3. **`README.md`**: Project overview and quick start
4. **`requirements.txt`**: Python dependencies
