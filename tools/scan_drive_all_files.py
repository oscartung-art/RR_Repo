"""
scan_drive_all_files.py — Scan all files in Google Drive (excluding temp folder),
index them by path, and compare against CurrentDB.gsheet to find missing entries.
"""
import json
import subprocess
import time

ROOT_FOLDER_ID = "1TNwfOEaOPYcZe9vXvfegMqkC2wU3QG2T"  # My Drive 'Database' folder
OUTPUT_FILE = "/home/ubuntu/drive_all_files_index.json"

# All active top-level folders (excluding temp)
TOP_FOLDERS = {
    "3Dsky":           "1bgJgAKfTc6qIr4HQOpHpYl6yUMkM7XF5",
    "AXYZ":            "1q7zaEP8ZG0_6bFZ58GvooyuBFu0Qx0K4",
    "dedon":           "1EQiRU0e0UUSAVx5DS4PzK0-_wQrch0iw",
    "designconnected": "1PcOnVy-4VHT_hVEpU6ejkR11rviyaYBE",
    "Dimensions":      "1ol5V2f2nkk-3zY2jcqsTjFBYUq2FSEn7",
    "dimensiva":       "1h5lDYQf46A-PL7LScjoDr292gnsbHzUM",
    "itoo":            "105210XvS28UR3EfgoQky28coNDXRFgCS",
    "Maxtree":         "1RAeVobxS9rmeG6WZrnFuJvngOxX18hEK",
    "Misc":            "12Mclccc6r2KKR-TbxAnGomnxnzw4p-J0",
    "Quixel":          "1mrX4Ox9I6OW6FB6CI07hRnWt3UeoOKuD",
    "twinmotion":      "1J7ots2wZs8KMtjc4Xc9vMKSH19SPY0Bt",
    "Wparallax":       "1E2PvB15Qjez2gPlPrjTeDMdCxMDX6hDH",
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}

def list_folder(folder_id, retries=3):
    items = []
    page_token = None
    while True:
        params = {
            "q": f'"{folder_id}" in parents and trashed = false',
            "fields": "nextPageToken,files(id,name,mimeType)",
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
            "pageSize": 1000,
        }
        if page_token:
            params["pageToken"] = page_token

        for attempt in range(retries):
            result = subprocess.run(
                ["gws", "drive", "files", "list", "--params", json.dumps(params)],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                break
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
        else:
            print(f"  ERROR listing folder {folder_id}: {result.stderr[:100]}")
            return items

        data = json.loads(result.stdout)
        items.extend(data.get("files", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return items

def scan_folder(folder_id, path_prefix, index, depth=0):
    """Recursively scan a folder and add ALL files to the index."""
    items = list_folder(folder_id)
    files_added = 0
    for item in items:
        name = item["name"]
        item_path = f"{path_prefix}/{name}" if path_prefix else name
        if item["mimeType"] == "application/vnd.google-apps.folder":
            sub_files = scan_folder(item["id"], item_path, index, depth + 1)
            files_added += sub_files
        else:
            # Index ALL files (not just images)
            lower_name = name.lower()
            ext = ""
            if "." in lower_name:
                ext = "." + lower_name.rsplit(".", 1)[1]
            index[item_path] = {
                "id": item["id"],
                "ext": ext,
                "is_image": ext in IMAGE_EXTS
            }
            files_added += 1
    return files_added

def main():
    index = {}
    total = 0
    for folder_name, folder_id in TOP_FOLDERS.items():
        print(f"Scanning {folder_name}...", flush=True)
        count = scan_folder(folder_id, folder_name, index)
        total += count
        print(f"  -> {count} files (total: {total})", flush=True)

    print(f"\nTotal files indexed: {len(index)}")
    with open(OUTPUT_FILE, "w") as f:
        json.dump(index, f)
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
