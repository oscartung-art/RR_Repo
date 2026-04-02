"""
fix_drive_filenames.py — Fix filename typos in Google Drive:
1. Remove '#' from designconnected filenames
2. Remove trailing space from Wparallax filename
"""
import json
import subprocess
import time
import os

# Files to rename: (current Drive path, new name)
RENAMES = [
    # designconnected - remove '#' character
    ("designconnected/10-03 # dining_chair-elliott_chair-kelly_wearstler.jpg",
     "10-03 dining_chair-elliott_chair-kelly_wearstler.jpg"),
    ("designconnected/10-06 Provocateur_Sofa #.jpg",
     "10-06 Provocateur_Sofa.jpg"),
    ("designconnected/10-07 gray07-gervasoni #.jpg",
     "10-07 gray07-gervasoni.jpg"),
    ("designconnected/10-07 ro5414-fritzhansen #.jpg",
     "10-07 ro5414-fritzhansen.jpg"),
    ("designconnected/10-11-# park_place_counter__9411.jpg",
     "10-11- park_place_counter__9411.jpg"),
    ("designconnected/10-13 # joco_stone_7481.jpg",
     "10-13 joco_stone_7481.jpg"),
    # Wparallax - remove trailing space
    ("Wparallax/wP_Retail_v2_R03_S_day .jpg",
     "wP_Retail_v2_R03_S_day.jpg"),
]

# Path to the drive index (relative to project root)
DRIVE_INDEX_PATH = os.path.join("db", "drive_all_files_index.json")

def get_file_id(path, drive_index):
    """Get file ID from the drive index."""
    info = drive_index.get(path)
    if info:
        return info["id"]
    # Try case-insensitive
    lower = path.lower()
    for k, v in drive_index.items():
        if k.lower() == lower:
            return v["id"]
    return None

def rename_file(file_id, new_name):
    """Rename a file in Drive using gws."""
    params = {
        "fileId": file_id,
        "supportsAllDrives": True,
    }
    body = {"name": new_name}
    result = subprocess.run(
        ["gws", "drive", "files", "update",
         "--params", json.dumps(params),
         "--json", json.dumps(body)],
        capture_output=True, text=True
    )
    return result.returncode == 0, result.stdout, result.stderr

def main():
    # Load drive index
    if not os.path.exists(DRIVE_INDEX_PATH):
        print(f"Error: Drive index not found at {DRIVE_INDEX_PATH}")
        return

    with open(DRIVE_INDEX_PATH) as f:
        drive_index = json.load(f)

    print(f"Processing {len(RENAMES)} renames...\n")
    success = 0
    errors = 0

    for old_path, new_name in RENAMES:
        file_id = get_file_id(old_path, drive_index)
        if not file_id:
            print(f"  NOT FOUND in index: {old_path}")
            errors += 1
            continue

        ok, stdout, stderr = rename_file(file_id, new_name)
        if ok:
            print(f"  OK: {old_path}")
            print(f"   -> {new_name}")
            success += 1
        else:
            print(f"  ERROR: {old_path}")
            print(f"   stderr: {stderr[:200]}")
            errors += 1
        time.sleep(0.5)

    print(f"\nDone: {success} renamed, {errors} errors")

if __name__ == "__main__":
    main()
