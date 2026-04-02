"""
--- SCRIPT: search_tag_assets.py ---
PURPOSE: Tag assets for Everything Search by writing vendor/rating metadata and .metadata.efu sidecars.

USAGE:
    1. Select files in Everything Search and press Ctrl+C to copy their paths.
    2. Run this script to tag the selected assets with vendor/rating/category info.
    3. The script updates .metadata.efu sidecars for Everything Search integration.

DEPENDENCIES: pandas, win32clipboard, os, hashlib, csv, ctypes
"""

import pandas as pd
import win32clipboard
import os
import hashlib
import csv
import ctypes
import builtins

# --- CONFIG ---
PARQUET_PATH = r"G:/_index.parquet"


def safe_print(*args, **kwargs):
    """Print without crashing on Windows terminals that are not UTF-8."""
    try:
        builtins.print(*args, **kwargs)
    except UnicodeEncodeError:
        sep = kwargs.get('sep', ' ')
        end = kwargs.get('end', '\n')
        text = sep.join(str(arg) for arg in args)
        fallback = text.encode('ascii', errors='replace').decode('ascii')
        builtins.print(fallback, end=end)


print = safe_print


def normalize_path(path):
    """Normalize paths for case-insensitive matching on Windows."""
    if path is None:
        return ""
    text = str(path).strip()
    if not text or text.lower() == "nan":
        return ""
    return os.path.normcase(os.path.normpath(text))


def ensure_brain_columns(df):
    """Ensure legacy parquet files still expose the columns the tagger needs."""
    if 'path' not in df.columns:
        df['path'] = ""
    if 'md5' not in df.columns:
        df['md5'] = ""
    if 'vendor' not in df.columns:
        df['vendor'] = ""
    if 'ratings' not in df.columns:
        if 'rating' in df.columns:
            df['ratings'] = df['rating']
        else:
            df['ratings'] = 0
    if 'category' not in df.columns:
        df['category'] = "Asset"

    df['path'] = df['path'].fillna("").astype(str)
    df['md5'] = df['md5'].fillna("").astype(str)
    df['vendor'] = df['vendor'].fillna("").astype(str)
    df['ratings'] = pd.to_numeric(df['ratings'], errors='coerce').fillna(0).astype(int)
    df['category'] = df['category'].fillna("Asset").astype(str)
    df['_norm_path'] = df['path'].apply(normalize_path)
    return df


def to_everything_rating(val):
    """Map 1-5 stars to Everything's expected rating values."""
    try:
        v = int(float(val))
    except Exception:
        return ""
    mapping = {1: 19, 2: 39, 3: 59, 4: 79, 5: 99}
    mapped = mapping.get(v, "")
    return str(mapped) if mapped else ""


def choose_best_match(df, mask):
    """Pick one row when the parquet contains duplicates for the same asset."""
    candidates = df[mask]
    if candidates.empty:
        return None

    scored = candidates.assign(
        _score=(candidates['md5'].str.len() > 0).astype(int) * 100
        + (candidates['vendor'].str.len() > 0).astype(int) * 10
        + candidates['ratings'].clip(lower=0, upper=5)
    )
    return scored.sort_values(by=['_score'], ascending=False).index[0]

def get_files_from_clipboard():
    """Grabs the file paths you copied in Everything Search."""
    win32clipboard.OpenClipboard()
    try:
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_HDROP):
            data = win32clipboard.GetClipboardData(win32clipboard.CF_HDROP)
            return [str(p) for p in data]
        
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
            raw = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            paths = [line.strip().strip('"') for line in raw.splitlines() if line.strip()]
            return paths
    finally:
        win32clipboard.CloseClipboard()
    return []

def get_file_hash(path):
    """Calculates DNA so tags stay permanent even if you move/rename the file."""
    hasher = hashlib.md5()
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except:
        return None

def update_display(df, modified_dirs=None, modified_md5s=None):
    """Generates sidecar .metadata.efu files for ALL files in modified directories."""
    print("\n📡 Exporting sidecar .metadata.efu files...")
    
    if not modified_dirs or len(modified_dirs) == 0:
        print("⚠️ No directories to export. Aborting.")
        return
    
    export_df = ensure_brain_columns(df.copy())
    
    export_df = export_df.rename(columns={
        'ratings': 'Rating', 
        'vendor': 'Album', 
        'category': 'Genre'
    })
    
    # Clean up empty values so they don't print as 'nan'
    export_df['Album'] = export_df['Album'].fillna("").astype(str)
    export_df['Genre'] = export_df['Genre'].fillna("").astype(str)
    
    export_df['Rating'] = export_df['Rating'].apply(to_everything_rating)
    
    # Drop any rows where path is missing
    export_df = export_df[export_df['path'].str.len() > 0]
    
    # Split paths into Directory and relative Filename
    export_df['Directory'] = export_df['path'].apply(lambda x: os.path.normpath(os.path.dirname(str(x))))
    export_df['Filename'] = export_df['path'].apply(lambda x: os.path.basename(str(x)))
    
    # Strict case-insensitive folder matching
    export_df['Dir_Match'] = export_df['Directory'].apply(lambda x: os.path.normcase(str(x)))
    
    # Filter to only the directories we touched (keep ALL files in those directories)
    if modified_dirs:
        safe_modified_dirs = {os.path.normcase(os.path.normpath(str(d))) for d in modified_dirs}
        print(f"  Exporting all files from modified directories: {[os.path.basename(d) for d in safe_modified_dirs]}")
        export_df = export_df[export_df['Dir_Match'].isin(safe_modified_dirs)]
        print(f"  Found {len(export_df)} total rows across those directories")
        if modified_md5s:
            print(f"  ({len(modified_md5s)} files were updated, rest preserve existing metadata)")
        
    if export_df.empty:
        print("⚠️ No rows found in modified directories.")
        return
    
    # Prefer rows that already have real metadata before removing duplicate filenames.
    export_df['_metadata_score'] = (
        (export_df['Album'].str.len() > 0).astype(int) * 100
        + pd.to_numeric(export_df['Rating'], errors='coerce').fillna(0).astype(int)
    )
    export_df = export_df.sort_values(by=['_metadata_score'], ascending=False)
    export_df = export_df.drop_duplicates(subset=['Directory', 'Filename'], keep='first')

    # FIX 1: Remove "Ghost" ZIPs from the original index before mirroring the correct tags
    export_df = export_df[~export_df['Filename'].str.lower().str.endswith('.zip', na=False)]
    
    # Dynamic extension to .zip translation
    zip_version = export_df.copy()
    zip_version['Filename'] = zip_version['Filename'].apply(lambda x: os.path.splitext(str(x))[0] + '.zip')
    
    final_display = pd.concat([export_df, zip_version]).drop_duplicates(subset=['Directory', 'Filename'])
    
    # Group by directory and write sidecars
    grouped = final_display.groupby('Directory')
    count = 0
    files_written = 0
    
    for directory, group in grouped:
        if not os.path.exists(directory):
            print(f"  ⚠️ Directory doesn't exist: {directory}")
            continue 
            
        efu_path = os.path.join(directory, '.metadata.efu')
        out_df = group[['Filename', 'Rating', 'Album', 'Genre']].copy()
        
        # FIX 2: Un-hide the file! Windows blocks Python from overwriting Hidden files.
        if os.path.exists(efu_path):
            try:
                ctypes.windll.kernel32.SetFileAttributesW(efu_path, 128) # 128 = NORMAL
            except:
                pass
        
        try:
            # FIX 3: QUOTE_ALL ensures Everything reads empty blanks correctly
            out_df.to_csv(efu_path, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
            
            # Verify file was written
            if os.path.exists(efu_path):
                file_size = os.path.getsize(efu_path)
                count += 1
                files_written += len(out_df)
                print(f"  ✅ Wrote .metadata.efu ({len(out_df)} entries, {file_size} bytes) in {os.path.basename(directory)}/")
            else:
                print(f"  ❌ File was not created: {efu_path}")
        except PermissionError:
            print(f"  ❌ Permission denied - file is locked!")
            print(f"     This usually means Everything Search or another program is using it.")
            print(f"     Solution: Close Everything Search, try again, then reopen it.")
        except Exception as e:
            print(f"  ❌ Error writing {efu_path}: {type(e).__name__}: {e}")
        
    if count == 0:
        print("\n❌ No .metadata.efu files were written!")
    else:
        print(f"\n✨ Successfully wrote {count} .metadata.efu files with {files_written} total entries!")

def run_tagger():
    print("--- ⭐ ASSET LIBRARIAN v2.5 (UNBLOCKED EDITION) ---")
    
    selected_paths = get_files_from_clipboard()
    if not selected_paths:
        print("❌ Clipboard empty! Select files in Everything and press Ctrl+C first.")
        return

    print(f"📦 Selected {len(selected_paths)} files.")
    for p in selected_paths[:3]:
        print(f"   - {p}")
    if len(selected_paths) > 3:
        print(f"   ... and {len(selected_paths) - 3} more")
    
    v = input("Enter Vendor (Enter to skip): ").strip()
    r_raw = input("Enter Rating 1-5 (Enter to skip): ").strip()
    r = None
    
    print(f"  Vendor: '{v}' {'(SKIPPED)' if not v else ''}")
    
    if r_raw:
        try:
            r_int = int(r_raw)
            if 1 <= r_int <= 5:
                r = r_int
                print(f"  Rating: {r}")
            else:
                print("⚠️ Rating must be between 1 and 5. Skipping.")
        except ValueError:
            print("⚠️ Invalid rating format. Skipping.")
    else:
        print("  Rating: (SKIPPED - will preserve existing ratings)")

    if not v and r is None:
        print("⚠️ No vendor or rating entered. Nothing to update.")
        return

    if not os.path.exists(PARQUET_PATH):
        print(f"❌ Brain not found at {PARQUET_PATH}.")
        return
    
    df = ensure_brain_columns(pd.read_parquet(PARQUET_PATH))
    print(f"📊 Loaded parquet with {len(df)} rows")

    matches = 0
    modified_dirs = set()
    modified_md5s = set()  # TRACK WHICH FILES WERE MODIFIED
    
    for path in selected_paths:
        if str(path).lower().endswith('.zip'):
            base_path = os.path.splitext(str(path))[0]
            target_path = None
            for ext in ['.jpg', '.jpeg', '.png']:
                if os.path.exists(base_path + ext):
                    target_path = base_path + ext
                    break
            if not target_path:
                print(f"⚠️ Could not find companion image for: {os.path.basename(str(path))}")
                continue
        else:
            target_path = path

        normalized_target = normalize_path(target_path)
        dna = get_file_hash(target_path)
        match_index = None
        match_reason = None

        if dna:
            md5_mask = df['md5'] == dna
            match_index = choose_best_match(df, md5_mask)
            if match_index is not None:
                match_reason = f"md5: {dna[:8]}..."

        if match_index is None:
            path_mask = df['_norm_path'] == normalized_target
            match_index = choose_best_match(df, path_mask)
            if match_index is not None:
                match_reason = "path fallback"
                if dna and not df.at[match_index, 'md5']:
                    df.at[match_index, 'md5'] = dna

        if match_index is not None:
            old_vendor = df.at[match_index, 'vendor']
            old_rating = df.at[match_index, 'ratings']
            print(f"  ✅ Found match for {os.path.basename(target_path)} ({match_reason})")
            print(f"     Before: Vendor='{old_vendor}', Rating={old_rating}")

            if v:
                df.at[match_index, 'vendor'] = v
            if r is not None:
                df.at[match_index, 'ratings'] = r

            new_vendor = df.at[match_index, 'vendor']
            new_rating = df.at[match_index, 'ratings']
            print(f"     After:  Vendor='{new_vendor}', Rating={new_rating}")

            df.at[match_index, 'path'] = os.path.normpath(target_path)
            df.at[match_index, '_norm_path'] = normalized_target
            matches += 1
            if dna:
                modified_md5s.add(dna)
            modified_dirs.add(os.path.normpath(os.path.dirname(target_path)))
        else:
            if dna:
                print(f"  ❌ No match in parquet for {os.path.basename(target_path)} (md5: {dna[:8]}..., no path fallback)")
            else:
                print(f"  ⚠️ Could not read file: {os.path.basename(target_path)}")
    
    print(f"\n📊 MATCH SUMMARY: {matches}/{len(selected_paths)} files matched")
    
    if matches > 0:
        print(f"  Modified directories: {modified_dirs}")
        print(f"  Modified MD5s: {len(modified_md5s)} unique files")
        print(f"\n  Saving parquet...")
        df.drop(columns=['_norm_path'], errors='ignore').to_parquet(PARQUET_PATH)
        print(f"  ✅ Parquet saved")
        
        print(f"\n  Calling update_display()...")
        update_display(df.drop(columns=['_norm_path'], errors='ignore'), modified_dirs, modified_md5s)
        print(f"\n✨ SUCCESS! Updated {matches} assets.")
        print(f"👉 In Everything Search, press 'F5' to instantly see your new stars.")
    else:
        print("\n❓ No matches found. This means the selected files don't have matching MD5s in the Brain.")
        print("   Possible causes:")
        print("   1. Files have been re-exported/modified since indexing (different bytes = different MD5)")
        print("   2. You selected .ZIP files without companion images")
        print("   3. Files are from a folder that hasn't been indexed yet")
        print("\n   Solution: Re-run index_master.py on the folder containing these files.")

if __name__ == "__main__":
    run_tagger()


