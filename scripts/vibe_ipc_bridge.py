import os
import time
import torch
import open_clip
import pandas as pd
import numpy as np
import ctypes
import win32clipboard
import winsound
from ctypes import wintypes

# --- CONFIG ---
INDEX_PATH = r"G:/_index.parquet"
MODEL_NAME = 'ViT-L-14'
PRETRAINED = 'openai'
MATCH_THRESHOLD = 0.20  # Lowered to ensure you get 30 results
TOP_K = 30

# Windows API Setup
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def get_everything_text():
    """Grabs the current text from the Everything Search bar."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd: return None
    
    # Check if we are actually in Everything
    class_name = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, class_name, 256)
    if "EVERYTHING" not in class_name.value.upper():
        return None

    # Find the Edit control (the search bar)
    edit_hwnd = user32.FindWindowExW(hwnd, None, "Edit", None)
    if not edit_hwnd: return None

    # Get text length and content
    length = user32.SendMessageW(edit_hwnd, 0x000E, 0, 0) # WM_GETTEXTLENGTH
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.SendMessageW(edit_hwnd, 0x000D, length + 1, buf) # WM_GETTEXT
    return buf.value

def set_clipboard(text):
    """Safely sets the clipboard for Everything Search."""
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
    finally:
        win32clipboard.CloseClipboard()

def run_bridge():
    print("🚀 VIBE BRIDGE STARTING...")
    
    # 1. Load AI & Brain
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, _, _ = open_clip.create_model_and_transforms(MODEL_NAME, pretrained=PRETRAINED)
    model = model.to(device).eval()
    tokenizer = open_clip.get_tokenizer(MODEL_NAME)
    
    print("🧠 Loading 30,000+ assets into GPU memory...")
    df = pd.read_parquet(INDEX_PATH)
    # Pre-stack vectors for instant math
    asset_vectors = np.stack(df['vector'].values).astype('float32')
    # Normalize them once at startup
    asset_vectors /= np.linalg.norm(asset_vectors, axis=1, keepdims=True)
    
    print("👂 Listening for 'vibe: ' in Everything Search...")
    last_query = ""

    while True:
        try:
            current_text = get_everything_text()
            
            if current_text and current_text.lower().startswith("vibe: "):
                query = current_text[6:].strip() # Remove 'vibe: '
                
                # Only process if user changed the query and stopped typing
                if query and query != last_query:
                    print(f"🔍 Searching for: {query}")
                    
                    # AI Math
                    with torch.no_grad():
                        text_tokens = tokenizer([query]).to(device)
                        text_features = model.encode_text(text_tokens)
                        text_features /= text_features.norm(dim=-1, keepdim=True)
                        q_vec = text_features.cpu().numpy().astype('float32').flatten()
                    
                    # Instant Similarity
                    scores = np.dot(asset_vectors, q_vec)
                    df['score'] = scores
                    
                    # Filter and Sort
                    results = df[df['score'] > MATCH_THRESHOLD].sort_values('score', ascending=False).head(TOP_K)
                    
                    if not results.empty:
                        # Join filenames with | (Everything's OR operator)
                        # We use just the filename (no ext) or exact path. Filename is safer for EFU.
                        filenames = []
                        for p in results['path']:
                            name = os.path.basename(p)
                            filenames.append(f'"{name}"')
                        
                        search_string = "|".join(filenames)
                        set_clipboard(search_string)
                        
                        winsound.MessageBeep(winsound.MB_ICONASTERISK)
                        print(f"🎯 {len(filenames)} matches copied to clipboard.")
                    
                    last_query = query
                    
        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(1)
            
        time.sleep(0.1) # Check every 100ms

if __name__ == "__main__":
    run_bridge()