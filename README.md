# RR Repo

Operational workspace for Real Rendering automation.

This repository combines:
- project management (markdown files per project)
- asset library tooling (indexing, semantic search, rating/tag sidecars)
- AI-powered asset ingestion and metadata enrichment

## What Is Active

Primary active areas are:
- `projects/` — per-project markdown records (flexible, no YAML)
- `scripts/` — asset indexing, search, and tagging
- `tools/` — project maintenance, asset ingestion, PDF processing

Historical and superseded utilities are kept in `archive/`.

## Quick Start

1. Create or activate virtual environment.
2. Install Python dependencies.
3. Ask Qwen Code to help you with any task!

Example (PowerShell):

```powershell
cd D:\RR_Repo
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Main Entry Points

### Project Management

All project data is stored in `projects/[CODE].md` as clean markdown.
Ask Qwen Code directly to read, update, or query any project file.

**Example queries:**
- "Show me KL1 contacts"
- "What's the status of PLS renderings?"
- "Add a note to MWR: client meeting scheduled"
- "Which projects have pending architect docs?"

### Asset Library Workflow

Key scripts:
- `scripts/search_index_master.py` — builds/updates G:\_index.parquet with CLIP vectors
- `scripts/search_clip_text.py` — semantic search against vectors
- `scripts/search_tag_assets.py` — writes vendor/rating metadata and .metadata.efu sidecars
- `scripts/search_everything_bridge.py` — IPC bridge for Everything-based flow

### Asset Ingestion

- `tools/ingest_asset.py` — AI-powered metadata enrichment (Ollama local, OpenRouter optional)

### Data / Sync Utilities

- `tools/audit_assets.py` — asset library audits
- `tools/audit_keywords.py` — keyword table validation

## Repository Layout (Current)

- `Shared/` — shared config/helpers
- `scripts/` — asset indexing/search/tagging
- `tools/` — operational automation (ingestion, audits, PDF processing)
- `projects/` — per-project markdown records
- `db/` — local data stores (Master_CRM.csv)
- `log/` — operational logs, notes, orphan reports
- `ipc/` — Everything Search SDK (DLL, header, examples)
- `scratch/` — temporary experiments
- `archive/` — superseded files
- `example/quotes/` — sample client quotations

## Security and Secrets

Rules:
- Never commit real API keys, tokens, or client secrets.
- Keep credential JSON local only.
- Use environment variables for runtime credentials.
- Use `.env.example` as a safe local template only.

## Maintenance Notes

- Python scripts should pass syntax validation before commit.
- Keep temporary experiments in `scratch/`, not `scripts/` or `tools/`.
- Move replaced scripts/docs into `archive/` instead of deleting blindly.
- Prefer updating existing entry points over introducing duplicate scripts.
- Project files are flexible markdown — no rigid schema, add sections as needed.

## Current Status (April 2026)

Recent repo cleanup completed:
- Removed all Google Sheets/Drive workflow dependencies
- Deleted pipeline/ (obsolete Gemini enrichment)
- Retired rr CLI system — replaced with natural language Qwen queries
- Converted all project files from YAML to clean, flexible markdown
- Updated ingest_asset.py — removed duplicate code, unused imports
