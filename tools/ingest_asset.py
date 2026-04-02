import os
import shutil
import hashlib
import csv
import argparse
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../') # Add parent directory to path
from Shared.config import DRIVE_D_THUMBNAILS, DRIVE_G_ASSET_MASS, DRIVE_E_REPO

# Configuration
ASSET_INDEX_CSV = os.path.join(DRIVE_E_REPO, "db", "Asset_Index.csv")

def generate_file_hash(filepath, hash_algo='sha256'):
    """Generates a hash for a given file."""
    hasher = hashlib.new(hash_algo)
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def check_for_duplicates(file_hash, master_index_path):
    """Checks if a file hash already exists in the master asset index."""
    if not os.path.exists(master_index_path):
        return False
    with open(master_index_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("ID") == file_hash: # Assuming ID column stores the hash
                return True
    return False

def rename_and_move_asset(original_zip_path, category, source, description, file_hash):
    """Renames the asset and its thumbnail, then moves them to the appropriate drives."""
    # Construct new base filename
    new_base_filename = f"{category}_{source}_{description}_{file_hash}"

    # Handle ZIP file
    new_zip_filename = f"{new_base_filename}.zip"
    target_zip_path = os.path.join(DRIVE_G_ASSET_MASS, new_zip_filename)
    os.makedirs(os.path.dirname(target_zip_path), exist_ok=True)
    shutil.move(original_zip_path, target_zip_path)
    print(f"Moved asset to: {target_zip_path}")

    # Handle JPG thumbnail
    original_jpg_path = os.path.splitext(original_zip_path)[0] + ".jpg"
    if os.path.exists(original_jpg_path):
        new_jpg_filename = f"{new_base_filename}.jpg"
        target_jpg_path = os.path.join(DRIVE_D_THUMBNAILS, category, new_jpg_filename) # Organize by category in D: drive
        os.makedirs(os.path.dirname(target_jpg_path), exist_ok=True)
        shutil.move(original_jpg_path, target_jpg_path)
        print(f"Moved thumbnail to: {target_jpg_path}")
    else:
        print("No matching JPG thumbnail found for the asset.")

    return new_base_filename

def update_master_index(master_index_path, asset_info):
    """Appends the new asset info to the master asset index CSV."""
    file_exists = os.path.exists(master_index_path)
    with open(master_index_path, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ["Category", "Source", "Description", "ID", "File Path", "Thumbnail Path"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()
        writer.writerow(asset_info)

def main():
    parser = argparse.ArgumentParser(description="Ingest and standardize 3D assets.")
    parser.add_argument("asset_path", help="Path to the original ZIP asset file.")
    args = parser.parse_args()

    original_zip_path = os.path.abspath(args.asset_path)

    if not os.path.exists(original_zip_path):
        print(f"Error: Asset file not found at {original_zip_path}")
        sys.exit(1)

    print(f"Starting ingestion for: {original_zip_path}")

    # 1. Generate hash
    file_hash = generate_file_hash(original_zip_path)
    print(f"Generated hash: {file_hash}")

    # 2. Check for duplicates
    if check_for_duplicates(file_hash, ASSET_INDEX_CSV):
        print("Warning: This asset (or its content) already exists in the master index. Skipping ingestion.")
        sys.exit(0)

    # 3. Prompt user for metadata
    category = input("Enter Asset Category (e.g., Furniture, Vegetation): ").strip()
    source = input("Enter Asset Source (e.g., 3dsky, Dimensiva): ").strip()
    description = input("Enter Asset Description (e.g., EamesLoungeChair): ").strip()

    if not all([category, source, description]):
        print("Error: Category, Source, and Description cannot be empty.")
        sys.exit(1)

    # 4. Rename and Move
    new_base_filename = rename_and_move_asset(original_zip_path, category, source, description, file_hash)
    
    # 5. Update Master Index
    asset_info = {
        "Category": category,
        "Source": source,
        "Description": description,
        "ID": file_hash, # Using hash as unique ID
        "File Path": os.path.join(DRIVE_G_ASSET_MASS, f"{new_base_filename}.zip"),
        "Thumbnail Path": os.path.join(DRIVE_D_THUMBNAILS, category, f"{new_base_filename}.jpg") if os.path.exists(os.path.splitext(original_zip_path)[0] + ".jpg") else ""
    }
    update_master_index(ASSET_INDEX_CSV, asset_info)
    print("Asset successfully ingested and master index updated.")

if __name__ == '__main__':
    main()
