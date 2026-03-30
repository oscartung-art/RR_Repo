import os
import shutil
import json
import csv
import argparse
from pathlib import Path

# Config
DEFAULT_G_DRIVE = "G:\\"
DEFAULT_D_DRIVE = "D:\\"
DEFAULT_DB_CSV = os.path.join("db", "Asset_Index.csv")

def parse_filename(filename):
    """Parses a filename into components based on [Category]_[Source]_[Description]_[ID] convention."""
    name_without_ext = os.path.splitext(filename)[0]
    parts = name_without_ext.split('_')
    
    if len(parts) >= 4:
        return {
            "Category": parts[0],
            "Source": parts[1],
            # Rejoin description if it contains underscores, except the last part which is ID
            "Description": "_".join(parts[2:-1]),
            "ID": parts[-1]
        }
    else:
        # Fallback for non-compliant names
        return {
            "Category": "Uncategorized",
            "Source": "Unknown",
            "Description": name_without_ext,
            "ID": "Unknown"
        }

def generate_sidecar_json(json_path, data):
    """Writes metadata to a .json file next to the asset."""
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def mirror_thumbnail(source_jpg, target_dir):
    """Copies a thumbnail from the G: drive to the D: drive."""
    if os.path.exists(source_jpg):
        os.makedirs(target_dir, exist_ok=True)
        filename = os.path.basename(source_jpg)
        target_jpg = os.path.join(target_dir, filename)
        
        # Only copy if it doesn't exist or is newer
        if not os.path.exists(target_jpg) or os.path.getmtime(source_jpg) > os.path.getmtime(target_jpg):
            shutil.copy2(source_jpg, target_jpg)
            return True
    return False

def update_asset_index(csv_path, assets_data):
    """Updates the Master Asset Index CSV with the new data."""
    file_exists = os.path.exists(csv_path)
    existing_ids = set()
    
    # Read existing IDs to prevent duplicates
    if file_exists:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_ids.add(row.get("ID"))
                
    # Append new records
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, mode='a', newline='', encoding='utf-8') as f:
        headers = ["Category", "Source", "Description", "ID", "File Path"]
        writer = csv.DictWriter(f, fieldnames=headers)
        
        if not file_exists:
            writer.writeheader()
            
        for asset in assets_data:
            if asset["ID"] not in existing_ids or asset["ID"] == "Unknown":
                writer.writerow(asset)
                existing_ids.add(asset["ID"])

def main():
    parser = argparse.ArgumentParser(description="Asset Metadata Harvester and Sync")
    parser.add_argument("--g-drive", default=DEFAULT_G_DRIVE, help="Source path for Asset Mass (G: Drive)")
    parser.add_argument("--d-drive", default=DEFAULT_D_DRIVE, help="Target path for Cloud Sync (D: Drive)")
    args = parser.parse_args()
    
    print(f"=== Scanning Assets on {args.g_drive} ===")
    
    assets_scanned = []
    thumbnails_mirrored = 0
    sidecars_created = 0
    
    # Walk the G: drive
    for root, dirs, files in os.walk(args.g_drive):
        for file in files:
            if file.endswith(".zip"):
                zip_path = os.path.join(root, file)
                
                # 1. Parse Metadata
                asset_metadata = parse_filename(file)
                asset_metadata["File Path"] = zip_path
                assets_scanned.append(asset_metadata)
                
                # 2. Generate JSON Sidecar
                json_path = os.path.splitext(zip_path)[0] + ".json"
                if not os.path.exists(json_path):
                    generate_sidecar_json(json_path, asset_metadata)
                    sidecars_created += 1
                
                # 3. Mirror Thumbnail
                jpg_path = os.path.splitext(zip_path)[0] + ".jpg"
                if mirror_thumbnail(jpg_path, args.d_drive):
                    thumbnails_mirrored += 1

    # 4. Update CSV
    update_asset_index(DEFAULT_DB_CSV, assets_scanned)
    
    print("=== Harvester Complete ===")
    print(f"[+] Total assets scanned: {len(assets_scanned)}")
    print(f"[+] New sidecars generated: {sidecars_created}")
    print(f"[+] Thumbnails mirrored to D:: {thumbnails_mirrored}")

if __name__ == "__main__":
    main()
