---
created: 2026-03-28
source: gemini-web
status: on-hold
executor: either
---

# Task: Everything Search Integration - EFU Export Script

## 1. Context
VoidTools Everything Search is the primary tool for asset discovery. To ensure search results are enriched with repository metadata, we need an automated way to convert the asset master database into an EFU (Everything File List) format. This allows for lightning-fast filtering of the G:\ drive assets.

## 2. What To Do
1. Create `tools/export_efu.py` in the RR_Repo.
2. The script must import `BRAIN_ROOT`, `SYNC_ROOT`, and `ASSET_ROOT` from `Shared.config`.
3. Locate the master `_index.csv` file within the `ASSET_ROOT` (G:\).
4. Parse the `_index.csv` and generate a standard EFU file.
   - EFU format header: `Filename,Size,Date Modified,Date Created,Attributes`
   - Map relative paths in the CSV to full absolute paths on G:\.
5. Save the output as `assets_index.efu` in the `SYNC_ROOT` (D:\GoogleDrive\RR_Repo\).

## 3. Files To Edit / Create
- CREATE: `tools/export_efu.py`
- OUTPUT: `assets_index.efu` (saved to Sync folder)

## 4. Done When
- [ ] `tools/export_efu.py` exists and runs without errors.
- [ ] A valid `assets_index.efu` is generated in the Sync folder.
- [ ] Opening the `.efu` file in Everything Search correctly displays the asset list with correct paths.

## 5. Hold Reason
`G:\_index.csv` does not yet exist. This task is blocked until the asset index CSV is created by `sync_assets.py` or equivalent.
