# RR Repo

Operational workspace for Real Rendering automation.

This repository combines:
- project operations tooling (dashboard, CRM sync, project metadata)
- asset library tooling (indexing, semantic search, rating/tag sidecars)
- Google Drive / Google Sheets automation
- a small command-line interface for daily workflows

## What Is Active

Primary active areas are:
- tools/rr package and tools/rr.py entry point (studio CLI)
- scripts for asset indexing, search, and tagging
- tools for project/CRM/sheet maintenance
- pipeline for Gemini-based metadata enrichment

Historical and superseded utilities are kept in archive.

## Quick Start

1. Create or activate virtual environment.
2. Install Python dependencies.
3. Set required environment variables.
4. Run the command or script you need.

Example (PowerShell):

```powershell
cd D:\GoogleDrive\RR_Repo
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r pipeline\requirements.txt
$env:GEMINI_API_KEY="<your-gemini-api-key>"
$env:GOOGLE_APPLICATION_CREDENTIALS="D:\GoogleDrive\RR_Repo\Shared\service-account.json"
```

## Main Entry Points

### RR CLI

Main dispatcher:
- tools/rr.py

Helpful commands:
- rr help
- rr p <CODE> [summary|docs|contacts|links|rend|ani|full]
- rr open <CODE>
- rr c <CODE> <category> <field>
- rr dash
- rr crm [search_term]
- rr log <CODE> <message>
- rr find <query_or_image>

Windows helper:
- p.bat now dispatches to tools/rr.py p

### Asset Library Workflow

Key scripts:
- scripts/index_master.py: builds/updates G:/_index.parquet and export CSV
- scripts/search_clip_text.py: semantic search against vectors
- scripts/tag_assets.py: writes vendor/rating metadata and .metadata.efu sidecars
- scripts/search_everything_bridge.py: IPC bridge for Everything-based flow

### Pipeline Workflow

Key scripts:
- pipeline/enrich_gdrive.py: Gemini metadata enrichment pipeline
- pipeline/process_folder.py: single-folder processing flow

### Data / Sync Utilities

Examples:
- tools/sync_crm.py
- tools/sync_assets.py
- tools/sync_gsheet_to_local_csv.py
- tools/update_project_index.py
- tools/rebuild_drive_index.py

## Repository Layout (Current)

- Shared/: shared config/helpers and local auth files
- scripts/: asset indexing/search/tagging + small operational scripts
- tools/: operational automation + rr CLI package
- pipeline/: enrichment pipeline scripts
- projects/: per-project markdown records
- example/quotes/: sample quotation markdown files for ingestion/automation prototyping
- db/: local data stores (Master_CRM.csv, projects.json)
- log/: operational logs, notes, orphan reports
- ipc/: Everything Search SDK (DLL, header, example projects)
- scratch/: temporary experiments and migration output
- archive/: superseded files retained for reference
- example/: sample client quotations for automation prototyping

## Security and Secrets

Rules:
- Never commit real API keys, tokens, or client secrets.
- Keep credential JSON local only.
- Use environment variables for runtime credentials.
- Use .env.example as a safe local template only.

Current .gitignore already excludes Shared/service-account.json and Shared/token*.json.

## Maintenance Notes

- Python scripts should pass syntax validation before commit.
- Keep temporary experiments in scratch, not scripts/tools.
- Move replaced scripts/docs into archive instead of deleting blindly.
- Prefer updating existing entry points over introducing duplicate scripts.

## Current Status (April 2026)

Recent repo hardening completed:
- fixed syntax/runtime issues in multiple utilities
- stabilized scripts/tag_assets.py matching and sidecar export behavior
- unified star rating scale to Everything-compatible values (19/39/59/79/99)
- sanitized and renamed local key helper template
- fixed broken p.bat dispatcher target
