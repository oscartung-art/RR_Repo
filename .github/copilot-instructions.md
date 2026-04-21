# Copilot instructions for RR_Repo

Purpose: concise, actionable guidance for future Copilot sessions working in this repository.

1) Setup / Build / Test / Lint
- Activate venv (PowerShell):
  cd D:\\RR_Repo
  .\\.venv\\Scripts\\Activate.ps1
  pip install -r requirements.txt

- Syntax check a single file: python -m py_compile tools/ingest_asset.py
- Run full tests (if pytest is installed): python -m pytest
- Run a single test file: python -m pytest tests/test_live_vision_path.py
  (If pytest is not available, many tests are runnable directly: python tests/test_live_vision_path.py)
- Ingest dry-run (preview only):
  python tools/ingest_asset.py --asset-type=furniture --dry-run IMAGE ARCHIVE
  Use --yes only after preview is correct.
- Keyword table/audit: python tools/audit_keywords.py
- Optional linters (not required by repo): flake8 . or ruff . if added to requirements.

2) High-level architecture (big picture)
- Entry points:
  - tools/ : operational automation - asset ingestion, indexing, building vector search (CLIP), semantic search, and tagging flows (tools/ingest_asset.py is the canonical ingest path).
  - Shared/ : shared configuration and helpers (Shared/config.py exposes env overrides).
  - projects/ : project records kept as freeform markdown.
  - manual/ : authoritative metadata conventions (especially everything_columnmapping.md).
  - db/ and Database/ : local data stores and EFU metadata stores.
- Data flow (simplified): ingestion -> metadata enrichment (tools/ingest_asset.py) -> write sidecar .metadata.efu + update indexes -> tools/* build semantic search/index (search vectors) -> queries from tools.
- Models: ingest_asset.py supports local Ollama use and optional online routes (OpenRouter); configure credentials externally.

3) Key repository-specific conventions
- Platform: Windows + PowerShell is the supported workflow; many scripts assume Windows paths.
- Dry-run-first: Always preview writes (tools/ingest_asset.py --dry-run) before applying with --yes.
- EFU/Everything metadata: Column names and semantics are canonical in manual/everything_columnmapping.md — write EFU output to use those exact headers.
- Subject/source-of-truth: Subject is AI-determined for all asset types and written as `AssetType/<AI subject>`. Do not rely on static prefix-code or subcategory mapping for Subject.
- Experiments & cleanup: use scratch/ for experiments; put replaced scripts/docs into archive/ rather than deleting.
- Secrets: never commit keys. Use environment variables and .env.example as template. Shared/config.py contains the override points.
- Small targeted edits: prefer surgical changes over broad refactors. Verify file paths before operating on assets.
- Tests: tests/ contains diagnostic/regression scripts; not all tests require pytest — some are run as standalone Python scripts.

4) AI-assistant & local-agent configs to consult
- AGENTS.md (this repo) contains agent guidelines and recurring commands — read it first.
- Other local rules referenced: .clinerules (local agent rules), .cursor/rules/, .windsurfrules, CONVENTIONS.md / AIDER_CONVENTIONS.md if present. Update AGENTS.md and manual/ when changing conventions.

5) Where to update this file
- If you change entry points, ingest behaviour, EFU mappings, or the primary test commands, update manual/* and AGENTS.md along with this file.

For quick context, see README.md, AGENTS.md, and manual/everything_columnmapping.md.
