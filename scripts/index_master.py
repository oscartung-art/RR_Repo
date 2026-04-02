import pandas as pd
import os
import torch
import open_clip
import hashlib
from PIL import Image
from tqdm import tqdm

# --- CONFIG ---
# These paths are set to your G: drive for portability
PARQUET_PATH = r"G:/_index.parquet"
EVERYTHING_CSV = r"G:/everything_metadata.csv"
EXTENSIONS = ('.jpg', '.jpeg', '.png')

def get_file_hash(path):
    """
    Calculates MD5 DNA. 
    This allows the system to remember tags even if you rename the file.
    """
    hasher = hashlib.md5()
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return None

def update_everything_display(df):
    """
    Synchronizes the Brain (Parquet) to Everything Search's UI (CSV).
    This runs automatically after indexing or cleanup.
    """
    print("\n📡 Syncing to Everything Search UI...")
    
    # Map our internal brain columns to Everything Property names
    mapping = {
        'path': 'Filename',
        'ratings': 'Rating',
        'vendor': 'Album',
        'category': 'Genre'
    }
    
    # Ensure columns exist in the dataframe
    for col in mapping.keys():
        if col not in df.columns: 
            df[col] = "" if col != 'ratings' else 0
    
    # Create the display export
    export_df = df.rename(columns=mapping)[['Filename', 'Rating', 'Album', 'Genre']]
    
    # Everything uses a 1-99 scale for stars (20=1star, 40=2star, 60=3star, 80=4star, 99=5star)
    # We use (Rating * 20) - 1 to map 1→19, 2→39, 3→59, 4→79, 5→99
    export_df['Rating'] = (pd.to_numeric(export_df['Rating'], errors='coerce').fillna(0) * 20) - 1
    
    # Save the CSV that Everything 1.5 is "watching"
    # (Image files only - zip linking is handled in tag_assets.py metadata.efu export)
    export_df.to_csv(EVERYTHING_CSV, index=False, encoding='utf-8-sig')
    print(f"✨ Everything Search display updated: {EVERYTHING_CSV}")

def main():
    print("--- 🛠️ ASSET MASTER v1.0 ---")
    
    # 1. LOAD OR INITIALIZE BRAIN
    if os.path.exists(PARQUET_PATH):
        print("🧠 Loading existing Brain...")
        df = pd.read_parquet(PARQUET_PATH)
        # Add MD5 column if missing from an old version
        if 'md5' not in df.columns: df['md5'] = None
    else:
        print("🆕 Creating New Brain (Clean Slate)...")
        df = pd.DataFrame(columns=['path', 'md5', 'vendor', 'ratings', 'category'])

    # 2. OPTIONAL CLEANUP
    print("\n🧹 Maintenance Options:")
    print("  [1] Clean legacy ZIP errors from Dimensiva")
    print("  [2] Remove entries for deleted files")
    print("  [3] Skip cleanup")
    cleanup = input("Choose (1-3): ").strip()
    
    if cleanup == '1':
        initial_len = len(df)
        # Deep filter: lowercase check + strip hidden characters
        mask_to_delete = (
            df['path'].str.lower().str.contains('dimensiva') & 
            df['path'].str.lower().str.strip().str.endswith('.zip')
        )
        df = df[~mask_to_delete]
        print(f"✅ Cleanup complete. Purged {initial_len - len(df)} legacy ZIP entries.")
    
    elif cleanup == '2':
        initial_len = len(df)
        # Remove entries for files that no longer exist on disk
        df = df[df['path'].apply(lambda x: os.path.exists(x) if pd.notna(x) else False)]
        purged = initial_len - len(df)
        print(f"✅ Cleanup complete. Removed {purged} entries for deleted files.")

    # 3. INTERACTIVE PATH SELECTION
    target_folders = []
    print("\n📂 Enter folders to index (e.g., G:\\3D\\Dimensiva).")
    print("👉 Type 'done' when you are finished adding paths.")
    
    while True:
        p = input("Path: ").strip().strip('"')
        if p.lower() == 'done': break
        if os.path.isdir(p):
            target_folders.append(p)
            print(f"✅ Added to queue: {p}")
        else:
            print("❌ Invalid directory. Try again or type 'done'.")

    # If no new folders, just update the display and exit
    if not target_folders:
        print("⏭️ No new paths provided. Updating Everything display...")
        update_everything_display(df)
        return

    # 4. SCAN FOLDERS FOR IMAGES
    all_files = []
    for folder in target_folders:
        for root, _, files in os.walk(folder):
            for f in files:
                if f.lower().endswith(EXTENSIONS):
                    all_files.append(os.path.normpath(os.path.join(root, f)))

    # 5. INITIALIZE AI (CLIP)
    print(f"🤖 Found {len(all_files)} images. Loading CLIP (ViT-L-14)...")
    print("   (This takes 30-60 seconds on first run)")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, _, preprocess = open_clip.create_model_and_transforms('ViT-L-14', pretrained='openai')
    model = model.to(device).eval()
    print(f"✨ CLIP ready. Processing with {device.upper()}...")

    # 6. INCREMENTAL PROCESSING
    existing_paths = set(df['path'].dropna().unique())
    new_data = []
    skipped = 0
    
    for full_path in tqdm(all_files, desc="Indexing Assets"):
        # Skip if this exact path is already indexed
        if full_path in existing_paths:
            skipped += 1
            continue
        
        # Calculate DNA to see if we've seen this content before (by hash)
        dna = get_file_hash(full_path)
        
        # Skip if MD5 is already in the database (Incremental Indexing - file was moved/renamed)
        if not dna or (dna in df['md5'].values):
            continue
            
        try:
            # Auto-Vendor Logic: Grabs the third part of the path (G:\3D\VendorName\...)
            parts = full_path.split(os.sep)
            vendor = parts[2] if len(parts) > 2 else "Unknown"

            new_data.append({
                'path': full_path, 
                'md5': dna, 
                'vendor': vendor, 
                'ratings': 0, 
                'category': 'Asset'
            })
        except Exception as e:
            print(f"⚠️ Error indexing {full_path}: {e}")

    # 7. SAVE TO PARQUET & EXPORT TO CSV
    if new_data:
        df = pd.concat([df, pd.DataFrame(new_data)], ignore_index=True)
        df.to_parquet(PARQUET_PATH)
        print(f"💾 Saved {len(new_data)} new assets to Brain.")
        if skipped > 0:
            print(f"⏭️ Skipped {skipped} already-indexed files.")
    else:
        df.to_parquet(PARQUET_PATH) # Save cleanup/state even if no new items
        if skipped > 0:
            print(f"✅ No new unique assets ({skipped} already indexed).")
        else:
            print("✅ No new unique assets found.")
    
    update_everything_display(df)
    print("\n🏁 Process Complete. Everything Search is now synced.")

if __name__ == "__main__":
    main()