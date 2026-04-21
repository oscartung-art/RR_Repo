---
name: ingest-asset
description: Runs tools/ingest_asset.py for asset ingestion. Use this when the user pastes thumbnail or asset file paths and wants to ingest them. Run dry-run first to show the preview, then ask the user to confirm before applying with --yes.
allowed-tools: shell, powershell
---

## ingest-asset

Run `tools/ingest_asset.py` from `D:\rr_repo`. The script handles all asset type detection, AI enrichment, and EFU writing automatically.

### Step 1 — dry-run (always first)

```
cd D:\rr_repo && .\.venv\Scripts\Activate.ps1 && python tools/ingest_asset.py --dry-run "<FILE1>" "<FILE2>" ...
```

Show the full output to the user, then ask: **"Preview looks good — apply?"**

### Step 2 — apply (after user confirms)

```
cd D:\rr_repo && .\.venv\Scripts\Activate.ps1 && python tools/ingest_asset.py --yes "<FILE1>" "<FILE2>" ...
```

### Notes
- Pass the file paths exactly as the user provides them.
- `--asset-type=TYPE` is optional — only add it if the user explicitly states the type. Valid: `furniture`, `fixture`, `vegetation`, `people`, `material`, `layouts`, `object`, `vehicle`, `vfx`
- The script auto-detects image-only vs pair mode based on what files are present.
