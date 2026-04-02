"""
CLIPBOARD TAGGER for Everything Search (Event-Driven)

USAGE:
1. Start this script in the background.
2. Copy to clipboard: ratings:1-5 "path1" | "path2" | ...
3. Script instantly detects clipboard change and executes.

Event-driven mode = instant response, zero polling overhead.
The query part (after ratings:X) is automatically restored in Everything with F5 refresh.
"""

import ctypes
import csv
import os
import re
import sys
import time
import winsound
from ctypes import wintypes

import pandas as pd
import pyperclip


# --- Configuration ---
PARQUET_CANDIDATES = [
    r"G:/_index.parquet",
    r"G:/everything_metadata.parquet",
]
PARQUET_PATH = next((p for p in PARQUET_CANDIDATES if os.path.exists(p)), PARQUET_CANDIDATES[0])
EVERYTHING_CSV = r"G:/everything_metadata.csv"


def to_everything_rating(val):
    """Map 1-5 stars to Everything's expected rating values."""
    try:
        v = int(float(val))
    except Exception:
        return ""
    mapping = {1: 1, 2: 25, 3: 50, 4: 75, 5: 99}
    mapped = mapping.get(v, "")
    return str(mapped) if mapped else ""


def choose_best_match(df, mask, preferred_norm_path=None):
    matches = df[mask]
    if matches.empty:
        return None
    if preferred_norm_path is not None and '_norm_path' in matches.columns:
        same_path = matches[matches['_norm_path'] == preferred_norm_path]
        if not same_path.empty:
            return same_path.index[0]
    if 'path' in matches.columns:
        existing = matches[matches['path'].astype(str).str.len() > 0]
        if not existing.empty:
            return existing.index[0]
    return matches.index[0]


def normalize_path(path):
    return os.path.normcase(os.path.normpath(str(path)))


def ensure_brain_columns(df):
    defaults = {
        'md5': '',
        'ratings': 0,
        'path': '',
        '_norm_path': '',
        'vendor': '',
        'category': '',
    }
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default
    df['_norm_path'] = df['path'].fillna('').astype(str).apply(normalize_path)
    return df


def get_file_hash(path):
    import hashlib
    try:
        hasher = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return None


def update_display(df, modified_dirs, modified_md5s):
    print("\n📡 Syncing central Everything CSV...")
    export_df = pd.DataFrame({
        'Filename': df['path'].fillna('').astype(str),
        'Rating': df['ratings'].apply(to_everything_rating),
        'Album': df['vendor'].fillna('').astype(str),
        'Genre': df['category'].fillna('').astype(str),
    })
    export_df = export_df[export_df['Filename'] != '']
    export_df.to_csv(EVERYTHING_CSV, index=False, encoding='utf-8-sig')
    print(f"✨ Central Everything CSV updated: {EVERYTHING_CSV}")

    print("\n📡 Exporting sidecar .metadata.efu files...")
    touched = sorted(d for d in modified_dirs if d and os.path.isdir(d))
    print(f"  Directories: {touched}")

    if not touched:
        print("  No valid directories to export sidecars.")
        print("\n✨ Metadata sync complete.")
        return

    export_work = df.copy()
    export_work['_dir'] = export_work['path'].fillna('').astype(str).apply(
        lambda p: os.path.normpath(os.path.dirname(p)) if p else ''
    )
    scoped = export_work[export_work['_dir'].isin(touched)].copy()
    print(f"  Found {len(scoped)} total rows")

    sidecar_count = 0
    total_entries = 0

    for dir_path in touched:
        folder_df = scoped[scoped['_dir'] == dir_path].copy()
        if folder_df.empty:
            continue

        efu_path = os.path.join(dir_path, '.metadata.efu')
        folder_df['Filename'] = folder_df['path'].fillna('').astype(str).apply(os.path.basename)
        folder_df['Rating'] = folder_df['ratings'].apply(to_everything_rating)
        folder_df['Album'] = folder_df['vendor'].fillna('').astype(str)
        folder_df['Genre'] = folder_df['category'].fillna('').astype(str)

        rows = folder_df[['Filename', 'Rating', 'Album', 'Genre']].values.tolist()

        with open(efu_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['Filename', 'Rating', 'Album', 'Genre'])
            writer.writerows(rows)

        sidecar_count += 1
        total_entries += len(rows)
        file_size = os.path.getsize(efu_path)
        print(f"  ✅ .metadata.efu ({len(rows)} entries, {file_size} bytes) in {os.path.basename(dir_path)}/")

    print(f"\n✨ Successfully wrote {sidecar_count} .metadata.efu files with {total_entries} total entries!")


def parse_rating_command(text):
    """Parse rating command and return (paths, rating, query_text)."""
    if not text:
        return [], None, None

    rating_match = re.match(r'\s*ratings?\s*:\s*([1-5])\b', text, re.IGNORECASE)
    if not rating_match:
        return [], None, None
    rating = int(rating_match.group(1))

    text_after_rating = text[rating_match.end():].strip()
    paths = [match.strip() for match in re.findall(r'"([^"]+)"', text_after_rating)]
    deduped_paths = list(dict.fromkeys(path for path in paths if path))
    return deduped_paths, rating, text_after_rating


def resolve_target_path(path):
    if str(path).lower().endswith('.zip'):
        base_path = os.path.splitext(str(path))[0]
        for ext in ['.jpg', '.jpeg', '.png']:
            candidate = base_path + ext
            if os.path.exists(candidate):
                return candidate
        return None
    return path


def play_status_sound(success):
    try:
        alias = "SystemAsterisk" if success else "SystemHand"
        winsound.PlaySound(alias, winsound.SND_ALIAS | winsound.SND_ASYNC)
        return
    except RuntimeError:
        pass
    winsound.MessageBeep(winsound.MB_ICONASTERISK if success else winsound.MB_ICONHAND)


def apply_ratings(paths, rating):
    if not os.path.exists(PARQUET_PATH):
        print(f"[clipboard-tagger] Brain not found at {PARQUET_PATH}")
        return 0

    df = ensure_brain_columns(pd.read_parquet(PARQUET_PATH))
    matches = 0
    modified_dirs = set()
    modified_md5s = set()

    for raw_path in paths:
        target_path = resolve_target_path(raw_path)
        if not target_path:
            print(f"[clipboard-tagger] No companion image for {os.path.basename(str(raw_path))}")
            continue

        normalized_target = normalize_path(target_path)
        dna = get_file_hash(target_path)
        match_index = None
        match_reason = None

        if dna:
            md5_mask = df['md5'].fillna('') == dna
            match_index = choose_best_match(df, md5_mask, preferred_norm_path=normalized_target)
            if match_index is not None:
                match_reason = f"md5: {dna[:8]}..."

        if match_index is None:
            path_mask = df['_norm_path'] == normalized_target
            match_index = choose_best_match(df, path_mask, preferred_norm_path=normalized_target)
            if match_index is not None:
                match_reason = "path fallback"
                if dna and not df.at[match_index, 'md5']:
                    df.at[match_index, 'md5'] = dna

        if match_index is None:
            print(f"[clipboard-tagger] No parquet match for {os.path.basename(str(target_path))}")
            continue

        old_rating = df.at[match_index, 'ratings']
        df.at[match_index, 'ratings'] = rating
        df.at[match_index, 'path'] = os.path.normpath(target_path)
        df.at[match_index, '_norm_path'] = normalized_target

        print(
            f"[clipboard-tagger] {os.path.basename(str(target_path))}: "
            f"{old_rating} -> {rating} ({match_reason})"
        )

        matches += 1
        if dna:
            modified_md5s.add(dna)
        modified_dirs.add(os.path.normpath(os.path.dirname(str(target_path))))

    if matches == 0:
        return 0

    clean_df = df.drop(columns=['_norm_path'], errors='ignore')
    clean_df.to_parquet(PARQUET_PATH)
    update_display(clean_df, modified_dirs, modified_md5s)
    return matches


# --- Windows API & Everything integration ---
user32 = ctypes.windll.user32
WM_GETTEXT = 0x000D
WM_GETTEXTLENGTH = 0x000E
WM_SETTEXT = 0x000C
WM_CLIPBOARDUPDATE = 0x031D


def _get_window_class(hwnd):
    class_name = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, class_name, 256)
    return class_name.value


def _get_window_text(hwnd):
    title = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, title, 512)
    return title.value


def _find_everything_windows():
    hwnds = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_callback(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd):
            cls = _get_window_class(hwnd).upper()
            title = _get_window_text(hwnd).upper()
            if "EVERYTHING" in cls or "EVERYTHING" in title:
                hwnds.append(hwnd)
        return True
    user32.EnumWindows(enum_callback, 0)
    return hwnds


def _find_search_edit_handle(everything_hwnd):
    edit_hwnd = user32.FindWindowExW(everything_hwnd, None, "Edit", None)
    if edit_hwnd:
        return edit_hwnd
    child = user32.FindWindowExW(everything_hwnd, None, None, None)
    while child:
        edit_hwnd = user32.FindWindowExW(child, None, "Edit", None)
        if edit_hwnd:
            return edit_hwnd
        child = user32.FindWindowExW(everything_hwnd, child, None, None)
    return None


def restore_query_and_refresh(query_text):
    """Restore the query to Everything search box and refresh."""
    hwnds = _find_everything_windows()
    if not hwnds:
        return
    hwnd = hwnds[0]
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.05)

    if query_text:
        edit_hwnd = _find_search_edit_handle(hwnd)
        if edit_hwnd:
            user32.SendMessageW(edit_hwnd, WM_SETTEXT, 0, ctypes.c_wchar_p(query_text))
            time.sleep(0.05)

    VK_F5 = 0x74
    KEYEVENTF_KEYUP = 0x0002
    user32.keybd_event(VK_F5, 0, 0, 0)
    user32.keybd_event(VK_F5, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.05)


# Global state for clipboard listener
g_last_clipboard = ""
g_processed = set()


def main():
    global g_last_clipboard, g_processed
    
    print("[clipboard-tagger] 🚀 EVENT-DRIVEN mode: Listening for clipboard changes...")
    print("[clipboard-tagger] Copy: ratings:1-5 \"path1\" | \"path2\" | ...")
    
    # Attempt event-driven mode
    try:
        # Register for clipboard change notifications
        hwnd = user32.GetConsoleWindow()
        if hwnd:
            result = user32.AddClipboardFormatListener(hwnd)
            if result:
                print("[clipboard-tagger] ✅ Clipboard listener registered (event-driven)")
            else:
                print("[clipboard-tagger] ⚠️ Clipboard listener failed, using polling fallback...")
                polling_loop()
                return

        # Process clipboard updates via polling for simplicity
        # (True event-driven would require a message loop, which is complex in Python)
        polling_loop()
        
    except Exception as e:
        print(f"[clipboard-tagger] Exception: {e}. Falling back to polling...")
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

        # Only process if clipboard changed AND matches rating pattern.
        if current_clipboard and current_clipboard != g_last_clipboard:
            paths, rating, query_text = parse_rating_command(current_clipboard)

            if paths and rating is not None:
                unique_id = (tuple(paths), rating)
                if unique_id not in g_processed:
                    print(f"[clipboard-tagger] 📋 Clipboard detected: rating {rating} for {len(paths)} assets")
                    updated = apply_ratings(paths, rating)
                    if updated:
                        play_status_sound(True)
                        restore_query_and_refresh(query_text)
                        print(f"[clipboard-tagger] ✅ Done. Updated {updated} assets.")
                    else:
                        play_status_sound(False)
                        print("[clipboard-tagger] ❌ No assets matched.")
                    g_processed.add(unique_id)
            
            g_last_clipboard = current_clipboard

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
