"""
CLIPBOARD TAGGER for Everything Search Metadata File (Event-Driven)

USAGE:
1. Start this script in the background.
2. Copy to clipboard: columnname:value filename.jpg | filename2.jpg | ...
3. Script instantly detects clipboard change and updates D:\DB\.metadata.efu

Supports single or multiple files (pipe-separated).
The metadata file is updated directly.
"""

import csv
import os
import re
import time
import winsound

import pyperclip


# --- Configuration ---
METADATA_FILE = r"D:\DB\.metadata.efu"


def to_everything_rating(val):
    """Map 1-5 stars to Everything's expected rating values."""
    try:
        v = int(float(val))
    except Exception:
        return "-"
    mapping = {1: 1, 2: 25, 3: 50, 4: 75, 5: 99}
    mapped = mapping.get(v, "-")
    return str(mapped) if mapped else "-"


def play_status_sound(success):
    try:
        alias = "SystemAsterisk" if success else "SystemHand"
        winsound.PlaySound(alias, winsound.SND_ALIAS | winsound.SND_ASYNC)
        return
    except RuntimeError:
        pass
    winsound.MessageBeep(winsound.MB_ICONASTERISK if success else winsound.MB_ICONHAND)


def parse_delete_command(text):
    """Parse delete command: delete: path1 | path2 | path3"""
    if not text:
        return []
    
    # Check if it starts with "delete:"
    if not text.lower().startswith('delete:'):
        return []
    
    # Extract paths after "delete:"
    after_delete = text[7:].strip()  # Remove "delete:"
    
    # Split by pipe
    paths = [p.strip() for p in after_delete.split('|')]
    
    # Extract filenames only
    filenames = []
    for path in paths:
        if path:
            fn = os.path.basename(path)
            if fn:
                filenames.append(fn)
    
    return filenames


def delete_metadata_entries(filenames):
    """Delete entries from metadata file, remove image files, and remove corresponding zip/rar files from g:/db"""
    if not os.path.exists(METADATA_FILE):
        print(f"[tagger] Metadata file not found: {METADATA_FILE}")
        return 0
    
    # Read metadata
    try:
        with open(METADATA_FILE, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception as e:
        print(f"[tagger] Error reading metadata: {e}")
        return 0
    
    if not rows:
        print(f"[tagger] No rows in metadata file")
        return 0
    
    deleted_count = 0
    crc_values_to_delete = []
    files_to_delete = []
    
    # Create lowercase mapping for comparison
    filenames_lower = [fn.lower() for fn in filenames]
    
    # Find matching rows and collect CRC-32 values
    rows_to_keep = []
    for row in rows:
        row_filename = row.get('Filename', '').lower()
        if row_filename in filenames_lower:
            crc_value = row.get('CRC-32', '').strip()
            if crc_value:
                crc_values_to_delete.append(crc_value)
                files_to_delete.append(row.get('Filename', ''))
            print(f"[tagger] ✓ Deleting entry: {row.get('Filename', '')}")
            deleted_count += 1
        else:
            rows_to_keep.append(row)
    
    if deleted_count == 0:
        print(f"[tagger] ✗ No matching files found in metadata")
        return 0
    
    # Write back metadata without deleted entries
    try:
        fieldnames = list(rows[0].keys()) if rows else []
        with open(METADATA_FILE, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_to_keep)
        print(f"[tagger] ✅ Metadata updated ({deleted_count} entries removed)")
    except Exception as e:
        print(f"[tagger] Error writing metadata: {e}")
        return 0
    
    # Delete image files from D:\DB\
    image_count = 0
    for filename in files_to_delete:
        filepath = os.path.join(r"D:\DB", filename)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                print(f"[tagger] ✓ Deleted image: {filename}")
                image_count += 1
            except Exception as e:
                print(f"[tagger] ✗ Error deleting {filename}: {e}")
    
    if image_count > 0:
        print(f"[tagger] ✅ Deleted {image_count} image file(s)")
    
    # Delete corresponding zip/rar files from g:/db
    zip_count = 0
    db_path = r"g:\db"
    
    if os.path.exists(db_path):
        for crc in crc_values_to_delete:
            try:
                # List all files in g:/db and find ones containing this CRC-32
                for filename in os.listdir(db_path):
                    if crc.upper() in filename.upper():
                        filepath = os.path.join(db_path, filename)
                        if os.path.isfile(filepath):
                            try:
                                os.remove(filepath)
                                print(f"[tagger] ✓ Deleted archive: {filename}")
                                zip_count += 1
                            except Exception as e:
                                print(f"[tagger] ✗ Error deleting {filename}: {e}")
            except Exception as e:
                print(f"[tagger] ✗ Error searching g:/db: {e}")
    else:
        print(f"[tagger] ⚠️ g:/db not found, skipping archive deletion")
    
    if zip_count > 0:
        print(f"[tagger] ✅ Deleted {zip_count} archive file(s)")
    
    return deleted_count


def parse_metadata_command(text):
    """Parse command like: columnname:<value> file1 | file2 | file3"""
    if not text:
        return [], None, None
    
    # Split by pipe
    parts = [p.strip() for p in text.split('|')]
    if not parts:
        return [], None, None
    
    # First part: columnname:<value> file1
    first_part = parts[0]
    
    # Find the colon
    colon_idx = first_part.find(':')
    if colon_idx == -1:
        return [], None, None
    
    column_name = first_part[:colon_idx].strip().lower()
    rest = first_part[colon_idx+1:].strip()
    
    if not rest:
        return [], None, None
    
    # Extract value (between < and >) and filenames
    # Pattern: <value> file1
    value_match = re.match(r'<([^>]*)>\s*(.*)', rest)
    if value_match:
        value =     value_match.group(1).strip()
        files_part = value_match.group(2).strip()
    else:
        # Fallback: split last token as filename, rest as value
        tokens = rest.split()
        last_token = tokens[-1]
        if '.' in last_token or '\\' in last_token or '/' in last_token:
            value = ' '.join(tokens[:-1])
            files_part = last_token
        else:
            return [], None, None
    
    filenames = []
    if files_part:
        fn = os.path.basename(files_part)
        if fn:
            filenames.append(fn)
    
    # Add remaining filenames from other parts
    for remaining_part in parts[1:]:
        remaining_part = remaining_part.strip()
        if remaining_part:
            fn = os.path.basename(remaining_part)
            if fn:
                filenames.append(fn)
    
    if not filenames:
        return [], None, None
    
    return filenames, column_name, value


def apply_metadata_update(filenames, column_name, value):
    """Update any column in D:\DB\.metadata.efu for multiple files"""
    if not os.path.exists(METADATA_FILE):
        print(f"[tagger] Metadata file not found: {METADATA_FILE}")
        return 0
    
    # Read with error handling for special characters
    try:
        with open(METADATA_FILE, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception as e:
        print(f"[tagger] Error reading metadata: {e}")
        return 0
    
    if not rows:
        print(f"[tagger] No rows in metadata file")
        return 0
    
    # Check if column exists
    available_columns = list(rows[0].keys()) if rows else []
    # Try exact match first, then case-insensitive match
    matching_column = None
    for col in available_columns:
        if col.lower() == column_name.lower():
            matching_column = col
            break
    
    if not matching_column:
        print(f"[tagger] ✗ Column '{column_name}' not found. Available: {', '.join(available_columns[:5])}...")
        return 0
    
    # Update all matching rows by filename
    matches = 0
    for filename in filenames:
        for row in rows:
            if row.get('Filename', '').lower() == filename.lower():
                old_value = row.get(matching_column, '-')
                
                # Just use the value as-is (user provides exact value)
                new_value = value
                
                row[matching_column] = new_value
                print(f"[tagger] ✓ {filename}[{matching_column}]: {old_value} -> {new_value}")
                matches += 1
                break
    
    if matches == 0:
        print(f"[tagger] ✗ No files found in metadata")
        return 0
    
    # Write back
    try:
        fieldnames = list(rows[0].keys()) if rows else []
        with open(METADATA_FILE, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"[tagger] ✅ Metadata saved ({matches} files updated)")
        return matches
    except Exception as e:
        print(f"[tagger] Error writing metadata: {e}")
        return 0


# Global state for clipboard listener
g_last_clipboard = ""
g_processed = set()


def main():
    global g_last_clipboard, g_processed
    
    print("[tagger] 🚀 Listening for clipboard changes...")
    print("[tagger] Copy: columnname:<value> filename.jpg | filename2.jpg | ...")
    print("[tagger] Examples:")
    print("[tagger]   rating:<99> Armchair.jpg")
    print("[tagger]   album:<MyAlbum> Armchair.jpg | Chair.jpg | Table.jpg")
    print("[tagger]   period:<Modern> file1.jpg | file2.jpg")
    print("[tagger]   delete: file1.jpg | file2.jpg | file3.jpg")
    print("[tagger] Rating values: 1=1star, 25=2star, 50=3star, 75=4star, 99=5star")
    print("[tagger] Delete removes entry from .efu and deletes corresponding zip/rar from g:/db")
    
    polling_loop()


def polling_loop():
    """Polling-based clipboard monitor."""
    global g_last_clipboard, g_processed
    CHECK_INTERVAL = 0.05
    
    while True:
        try:
            current_clipboard = pyperclip.paste().strip()
        except Exception:
            time.sleep(CHECK_INTERVAL)
            continue

        # Only process if clipboard changed AND contains colon pattern
        if current_clipboard and current_clipboard != g_last_clipboard:
            # Quick check: only process if it contains the columnname: pattern
            if ':' not in current_clipboard:
                g_last_clipboard = current_clipboard
                time.sleep(CHECK_INTERVAL)
                continue
            
            # Check for delete command
            if current_clipboard.lower().startswith('delete:'):
                filenames = parse_delete_command(current_clipboard)
                if filenames:
                    unique_id = ('delete', tuple(filenames))
                    if unique_id not in g_processed:
                        print(f"[tagger] 📋 Delete command: {len(filenames)} file(s)")
                        success = delete_metadata_entries(filenames)
                        if success > 0:
                            play_status_sound(True)
                        else:
                            play_status_sound(False)
                        g_processed.add(unique_id)
            else:
                # Regular metadata update command
                filenames, column_name, value = parse_metadata_command(current_clipboard)
                if filenames and column_name and value is not None:
                    unique_id = (tuple(filenames), column_name, value)
                    if unique_id not in g_processed:
                        print(f"[tagger] 📋 Detected: {column_name}='<{value}>' for {len(filenames)} file(s)")
                        success = apply_metadata_update(filenames, column_name, value)
                        if success > 0:
                            play_status_sound(True)
                        else:
                            play_status_sound(False)
                        g_processed.add(unique_id)
            
            g_last_clipboard = current_clipboard

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
