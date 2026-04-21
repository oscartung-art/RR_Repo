import os
import re
import time
import ctypes
from pathlib import Path

import numpy as np
import open_clip
import pandas as pd
import torch
import pyperclip
import winsound

# --- CONFIG ---
INDEX_PATH = os.environ.get("RR_INDEX_PATH", r"G:/_index.parquet")
MODEL_NAME = 'ViT-L-14'
PRETRAINED = 'openai'
MATCH_THRESHOLD = 0.22  # Raised for higher confidence, fewer false positives
TOP_K = 30
QUERY_PREFIX = os.environ.get("RR_BRIDGE_PREFIX", "").strip()
if not QUERY_PREFIX:
    QUERY_PREFIX = "vibe:"

user32 = ctypes.windll.user32

WM_SETTEXT = 0x000C


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


def extract_query(text):
    """Extract query from clipboard text using prefix routing."""
    if not text:
        return None

    stripped = text.strip()
    if not stripped:
        return None

    if QUERY_PREFIX:
        prefix_pattern = re.escape(QUERY_PREFIX)
        match = re.match(rf"^\s*{prefix_pattern}\s*(.+?)\s*$", stripped, flags=re.IGNORECASE)
        if not match:
            return None
        query = match.group(1).strip()
        return query or None

    return stripped


def push_query_to_everything(search_string):
    """Inject generated query into Everything search box and refresh."""
    hwnds = _find_everything_windows()
    if not hwnds:
        return False

    hwnd = hwnds[0]
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.05)

    edit_hwnd = _find_search_edit_handle(hwnd)
    if not edit_hwnd:
        return False

    user32.SendMessageW(edit_hwnd, WM_SETTEXT, 0, ctypes.c_wchar_p(search_string))
    time.sleep(0.05)

    VK_F5 = 0x74
    KEYEVENTF_KEYUP = 0x0002
    user32.keybd_event(VK_F5, 0, 0, 0)
    user32.keybd_event(VK_F5, 0, KEYEVENTF_KEYUP, 0)
    return True


def run_bridge():
    print("VIBE BRIDGE STARTING (clipboard mode)...")

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

    print(f"Watching clipboard for: '{QUERY_PREFIX} <query>'")
    print("Example: vibe: leather sofa white studio")

    last_clipboard = ""
    processed_queries = set()

    try:
        while True:
            try:
                current_clipboard = pyperclip.paste().strip()
            except Exception:
                time.sleep(0.1)
                continue

            if current_clipboard and current_clipboard != last_clipboard:
                query = extract_query(current_clipboard)
                if query and query not in processed_queries:
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
                        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                    else:
                        search_string = build_everything_query(results["path"].tolist())
                        if push_query_to_everything(search_string):
                            winsound.MessageBeep(winsound.MB_ICONASTERISK)
                            print(f"Pushed {len(results)} matches to Everything search.")
                        else:
                            winsound.MessageBeep(winsound.MB_ICONHAND)
                            print("Everything window/search box not found.")

                    processed_queries.add(query)

                last_clipboard = current_clipboard

            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Stopped.")

if __name__ == "__main__":
    run_bridge()