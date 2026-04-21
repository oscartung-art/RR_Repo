---
name: move-delete-assets
description: Moves or deletes asset files (thumbnail + archive) and keeps .metadata.efu in sync. Use when the user pastes image paths and says "move to X folder" or "delete these". Move updates Album to the destination folder name. Delete removes EFU entries only — user deletes files manually.
allowed-tools: shell, powershell
---

## move-delete-assets

Use this skill when the user wants to **move** assets to a different folder or **delete** EFU entries for assets they will remove manually.

### SKILL_DIR
`D:\rr_repo\.github\skills\move-delete-assets`

---

## Move assets

When the user says "move these to G:\DB\misc\" (or any destination):

```
python "D:\rr_repo\.github\skills\move-delete-assets\move_delete_assets.py" --move "DEST_DIR" "FILE1" "FILE2" ...
```

What happens:
- Thumbnail (image) is moved to DEST_DIR
- Matching archive (same stem, any asset extension) is moved to DEST_DIR
- Source `.metadata.efu`: rows for those files are removed
- Dest `.metadata.efu`: rows are added with **Album** set to the destination folder name
- `D:\RR_Repo\Database\.metadata.efu` (central index): Filename paths updated, Album updated

### Example

> "move these to G:\DB\misc\
> G:\DB\project\Bed_Flou_10965538.jpg
> G:\DB\project\Bed_EE43A3EE.jpg"

**Step 1 — dry-run (always first):**
```
python "D:\rr_repo\.github\skills\move-delete-assets\move_delete_assets.py" --move "G:\DB\misc\" --dry-run "G:\DB\project\Bed_Flou_10965538.jpg" "G:\DB\project\Bed_EE43A3EE.jpg"
```

Show output to user, then ask: **"Preview looks good — apply the move?"**

**Step 2 — apply:**
```
python "D:\rr_repo\.github\skills\move-delete-assets\move_delete_assets.py" --move "G:\DB\misc\" "G:\DB\project\Bed_Flou_10965538.jpg" "G:\DB\project\Bed_EE43A3EE.jpg"
```

---

## Delete EFU entries

When the user says "delete these" or "remove from index":

```
python "D:\rr_repo\.github\skills\move-delete-assets\move_delete_assets.py" --delete "FILE1" "FILE2" ...
```

What happens:
- Rows removed from the co-located `.metadata.efu` in each file's directory
- Rows removed from `D:\RR_Repo\Database\.metadata.efu` (central index)
- **Actual files are NOT deleted** — user does that manually

### Example

> "delete EFU entries for these:
> G:\DB\misc\OldChair_ABC123.jpg"

**Step 1 — dry-run:**
```
python "D:\rr_repo\.github\skills\move-delete-assets\move_delete_assets.py" --delete --dry-run "G:\DB\misc\OldChair_ABC123.jpg"
```

**Step 2 — apply:**
```
python "D:\rr_repo\.github\skills\move-delete-assets\move_delete_assets.py" --delete "G:\DB\misc\OldChair_ABC123.jpg"
```

---

## Important notes

- **Always dry-run first**, then ask the user to confirm before applying.
- The `Album` column is always set to the **destination folder's name** (e.g. folder `G:\DB\misc\` → Album = `misc`).
- If no archive is found for an image, only the image is moved and the EFU row is still synced.
- Files from multiple source directories are handled in a single run.
- The script also updates `D:\RR_Repo\Database\.metadata.efu` (the central index with full-path Filename values) automatically.
