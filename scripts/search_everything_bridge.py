import os
import re
import time
import ctypes
from pathlib import Path

import numpy as np
import open_clip
import pandas as pd
import torch
import win32clipboard
import winsound

# --- CONFIG ---
INDEX_PATH = os.environ.get("RR_INDEX_PATH", r"G:/_index.parquet")
MODEL_NAME = 'ViT-L-14'
PRETRAINED = 'openai'
MATCH_THRESHOLD = 0.22  # Raised for higher confidence, fewer false positives
TOP_K = 30
QUERY_PREFIX = os.environ.get("RR_BRIDGE_PREFIX", "").strip()
QUERY_STABLE_SECONDS = float(os.environ.get("RR_QUERY_STABLE_SECONDS", "0.35"))

user32 = ctypes.windll.user32

WM_GETTEXT = 0x000D
WM_GETTEXTLENGTH = 0x000E
VK_RETURN = 0x0D


def candidate_index_paths():
    """Build a prioritized list of possible parquet locations."""
    repo_root = Path(__file__).resolve().parents[1]
    return [
        Path(INDEX_PATH),
        Path(r"G:/_index.parquet"),
        repo_root / "_index.parquet",
        repo_root / "db" / "_index.parquet",
        repo_root / "scratch" / "_index.parquet",
    ]


def resolve_index_path():
    """Find the first existing parquet file from known candidates."""
    for path in candidate_index_paths():
        if path.exists():
            return path
    return None


def quote_everything_term(text):
    escaped = str(text).replace('"', '""')
    return f'"{escaped}"'


def build_everything_query(paths):
    """Prefer full path terms when available, fallback to filename."""
    terms = []
    for raw_path in paths:
        raw_path = str(raw_path)
        if not raw_path:
            continue
        path_obj = Path(raw_path)
        term = raw_path if path_obj.exists() else path_obj.name
        terms.append(quote_everything_term(term))
    # Keep order but deduplicate.
    deduped = list(dict.fromkeys(terms))
    return "|".join(deduped)


def load_and_prepare_index(index_path):
    """Load parquet and return a normalized vector matrix."""
    df = pd.read_parquet(index_path)

    if "vector" not in df.columns or "path" not in df.columns:
        raise ValueError("Index must contain 'path' and 'vector' columns.")

    df = df[df["vector"].notna() & df["path"].notna()].copy()
    if df.empty:
        raise ValueError("Index has no searchable rows.")

    vectors = np.stack(df["vector"].values).astype("float32")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    vectors /= norms
    return df, vectors

def _get_window_class(hwnd):
    class_name = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, class_name, 256)
    return class_name.value


def _get_window_text(hwnd):
    title = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, title, 512)
    return title.value


def _read_control_text(hwnd):
    if not hwnd:
        return None
    length = user32.SendMessageW(hwnd, WM_GETTEXTLENGTH, 0, 0)
    if length <= 0:
        return None
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.SendMessageW(hwnd, WM_GETTEXT, length + 1, buf)
    text = buf.value.strip()
    return text or None


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

    # Fallback for UI variants where search input is nested.
    child = user32.FindWindowExW(everything_hwnd, None, None, None)
    while child:
        edit_hwnd = user32.FindWindowExW(child, None, "Edit", None)
        if edit_hwnd:
            return edit_hwnd
        child = user32.FindWindowExW(everything_hwnd, child, None, None)
    return None


def get_everything_text():
    """Read current query text from Everything, preferring foreground window then fallback scan."""
    hwnd = user32.GetForegroundWindow()
    if hwnd:
        cls = _get_window_class(hwnd).upper()
        if "EVERYTHING" in cls:
            text = _read_control_text(_find_search_edit_handle(hwnd))
            if text:
                return text

    for everything_hwnd in _find_everything_windows():
        text = _read_control_text(_find_search_edit_handle(everything_hwnd))
        if text:
            return text
    return None


def extract_query(text):
    """Extract query from Everything text using optional prefix routing."""
    if not text:
        return None

    stripped = text.strip()
    if not stripped:
        return None

    # Prefix mode: set RR_BRIDGE_PREFIX=vibe: to only process prefixed commands.
    if QUERY_PREFIX:
        prefix_pattern = re.escape(QUERY_PREFIX)
        match = re.match(rf"^\s*{prefix_pattern}\s*(.+?)\s*$", stripped, flags=re.IGNORECASE)
        if not match:
            return None
        query = match.group(1).strip()
        return query or None

    # Default mode: any non-empty query in Everything is accepted.
    return stripped


def set_clipboard(text):
    """Safely sets the clipboard for Everything Search."""
    for _ in range(10):
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
                return
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            time.sleep(0.05)
    raise RuntimeError("Clipboard is busy. Could not write search query.")


def run_bridge():
    print("VIBE BRIDGE STARTING...")

    index_path = resolve_index_path()
    if not index_path:
        print("Error: Could not locate _index.parquet.")
        print("Set RR_INDEX_PATH or place the file at G:/_index.parquet.")
        return

    print(f"Using index: {index_path}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, _, _ = open_clip.create_model_and_transforms(MODEL_NAME, pretrained=PRETRAINED)
    model = model.to(device).eval()
    tokenizer = open_clip.get_tokenizer(MODEL_NAME)

    print("Loading index vectors...")
    df, asset_vectors = load_and_prepare_index(index_path)
    print(f"Loaded {len(df)} assets.")

    if QUERY_PREFIX:
        print(f"Listening in prefix mode: '{QUERY_PREFIX} <query>'")
    else:
        print("Listening in direct mode: type query in Everything and press Enter.")

    last_query = ""
    last_seen_text = ""
    last_change_time = time.time()
    last_enter_down = False
    last_probe = 0.0

    try:
        while True:
            current_text = get_everything_text()
            now = time.time()

            if current_text != last_seen_text:
                last_seen_text = current_text or ""
                last_change_time = now

            enter_down = bool(user32.GetAsyncKeyState(VK_RETURN) & 0x8000)
            enter_pressed = enter_down and not last_enter_down
            last_enter_down = enter_down

            query = extract_query(current_text)
            should_process = query and query != last_query and enter_pressed

            if should_process:
                print(f"Searching for: {query}")

                with torch.no_grad():
                    text_tokens = tokenizer([query]).to(device)
                    text_features = model.encode_text(text_tokens)
                    text_features /= text_features.norm(dim=-1, keepdim=True)
                    query_vector = text_features.cpu().numpy().astype("float32").flatten()

                scores = np.dot(asset_vectors, query_vector)
                working_df = df.copy()
                working_df["score"] = scores

                results = (
                    working_df[working_df["score"] > MATCH_THRESHOLD]
                    .sort_values("score", ascending=False)
                    .head(TOP_K)
                )

                if results.empty:
                    print("No matches above threshold.")
                else:
                    search_string = build_everything_query(results["path"].tolist())
                    set_clipboard(search_string)
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                    print(f"Copied {len(results)} matches to clipboard.")

                last_query = query
            elif not current_text:
                if now - last_probe > 5:
                    if QUERY_PREFIX:
                        print(f"Waiting for Everything search box... (type '{QUERY_PREFIX} your query')")
                    else:
                        print("Waiting for Everything search box... (type query and press Enter)")
                    last_probe = now

            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Stopped.")

if __name__ == "__main__":
    run_bridge()