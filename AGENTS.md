# AGENTS Guide for RR_Repo

This file helps AI coding agents work safely and productively in this repository.

## Start Here

- OS/workflow: Windows + PowerShell.
- Activate environment:
  - `cd D:\RR_Repo`
  - `.\.venv\Scripts\Activate.ps1`
- Install dependencies:
  - `pip install -r requirements.txt`

## High-Value References

- Project overview and entry points: [README.md](README.md)
- Canonical EFU column mapping: [manual/everything_columnmapping.md](manual/everything_columnmapping.md)
- Existing local agent rules: [.clinerules](.clinerules)

Use those docs as source of truth. Link to them instead of duplicating large tables in code comments.

## Repository Map (Operational)

- [tools](tools): ingestion, indexing, search, tagging, audits, migration utilities
- [Shared](Shared): shared config/helpers
- [projects](projects): per-project markdown records
- [manual](manual): authoritative metadata conventions
- [db](db) and [Database](Database): data stores and EFU metadata
- [tests](tests): diagnostic/regression scripts
- [archive](archive): superseded scripts/docs (prefer move over delete)

## Ingestion Workflow Rules

Primary ingestion entry point is [tools/ingest_asset.py](tools/ingest_asset.py).

- Prefer dry-run first for any ingest change:
  - `python tools/ingest_asset.py --dry-run --asset-type=furniture IMAGE ARCHIVE`
- Use `--yes` only after preview is correct.
- Image-only input is for re-enrich flows of already indexed files.
- Keep EFU writes aligned with canonical column names from [manual/everything_columnmapping.md](manual/everything_columnmapping.md).
- Subject is AI-determined for all asset types and stored as `AssetType/<AI subject>`; do not reintroduce static taxonomy or prefix-code mapping for Subject.

## GitHub Copilot Skills (Clipboard Watcher)

The repository provides specialized skills for common asset workflows via the clipboard watcher daemon:

### **extract-schedule-json** — Extract metadata from schedule PDFs to JSON

**Purpose:** Step 1 of two-step schedule workflow - parses PDF and generates JSON keyed by code name.

**Usage:**
```powershell
# Preview extraction (always run first)
python tools/extract_schedule_json.py --dry-run "path/to/schedule.pdf"

# Write JSON file after confirming preview
python tools/extract_schedule_json.py --yes "path/to/schedule.pdf"
```

**Output:** `schedule.json` in same directory as PDF, formatted as:
```json
{
  "PL-01": {"subject": "Material/...", "title": "...", "brand": "...", "color": "...", "location": "...", "dimension": "...", "code": "PL-01"},
  "PL-02": {...}
}
```

**Next steps:**
1. Review/edit JSON if needed
2. Extract images: `"schedule.pdf" create:` (via clipboard watcher)
3. Enrich: `"folder/" "metadata.json" enrich:` (via clipboard watcher)

### **Other Available Skills**

- **ingest-asset**: Runs `tools/ingest_asset.py` for asset ingestion with dry-run preview
- **ingest-schedule**: Converts schedule PDFs to EFU with AI enrichment (legacy single-step workflow)
- **edit-efu-metadata**: Updates fields in `.metadata.efu` files for specific assets
- **move-delete-assets**: Moves/deletes assets and syncs EFU metadata

Skill documentation: [`.github/skills/`](.github/skills/)

## Commands Agents Should Use Frequently

- Syntax check changed Python files:
  - `python -m py_compile tools/ingest_asset.py`
- Ingest dry-run sanity check:
  - `python tools/ingest_asset.py --asset-type=furniture --dry-run --yes IMAGE ARCHIVE`
- Keyword table audit:
  - `python tools/audit_keywords.py`
- Display CSV/EFU tables neatly in terminal:
  - `python tools/csvlook.py <file.efu|csv> [--lines N]`
  - **Always use this tool** when displaying table data (`.metadata.efu`, `.csv`)
- Extract schedule metadata to JSON:
  - `python tools/extract_schedule_json.py --dry-run "schedule.pdf"` (preview)
  - `python tools/extract_schedule_json.py --yes "schedule.pdf"` (write)

## Project-Specific Guardrails

- Never guess file paths; verify first.
- Keep temporary experiments in [scratch](scratch), not in [tools](tools).
- Move replaced logic/docs to [archive](archive) instead of deleting blindly.
- Do not commit secrets/tokens/API keys.
- Prefer small, targeted edits over broad refactors.

## Environment Notes

- The workflow commonly uses separate base paths for thumbnails and archives.
- If needed, ingestion paths can be overridden via environment variables (see [Shared/config.py](Shared/config.py)).
- Live AI enrichment requires valid runtime API credentials when online model calls are used.
