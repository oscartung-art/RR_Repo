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

- [tools](tools): ingestion, audits, migration utilities
- [scripts](scripts): indexing/search/tagging automation
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

## Commands Agents Should Use Frequently

- Syntax check changed Python files:
  - `python -m py_compile tools/ingest_asset.py`
- Ingest dry-run sanity check:
  - `python tools/ingest_asset.py --asset-type=furniture --dry-run --yes IMAGE ARCHIVE`
- Keyword table audit:
  - `python tools/audit_keywords.py`

## Project-Specific Guardrails

- Never guess file paths; verify first.
- Keep temporary experiments in [scratch](scratch), not in [tools](tools) or [scripts](scripts).
- Move replaced logic/docs to [archive](archive) instead of deleting blindly.
- Do not commit secrets/tokens/API keys.
- Prefer small, targeted edits over broad refactors.

## Environment Notes

- The workflow commonly uses separate base paths for thumbnails and archives.
- If needed, ingestion paths can be overridden via environment variables (see [Shared/config.py](Shared/config.py)).
- Live AI enrichment requires valid runtime API credentials when online model calls are used.
