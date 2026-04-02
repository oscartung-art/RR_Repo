import pandas as pd
import torch
import open_clip
import win32clipboard
import numpy as np
import os
import sys

# --- CONFIG ---
PARQUET_PATH = r"G:/_index.parquet"
MODEL_NAME = 'ViT-L-14'
PRETRAINED = 'openai'

def set_clipboard(text):
    """Copies the file path to the Windows clipboard."""
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
    finally:
        win32clipboard.CloseClipboard()

def find_asset():
    print("--- 🔍 VIBE SEARCH v1.0 ---")
    
    if not os.path.exists(PARQUET_PATH):
        print(f"❌ Brain not found at {PARQUET_PATH}. Please run index_master.py first.")
        return

    # 1. LOAD THE BRAIN
    print("🧠 Loading Brain into memory...")
    df = pd.read_parquet(PARQUET_PATH)
    
    # 2. USER INPUT
    query_text = input("\n✨ Describe the vibe you want: ").strip()
    if not query_text:
        return

    # 3. INITIALIZE CLIP
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🤖 Waking up CLIP on {device.upper()}...")
    
    model, _, preprocess = open_clip.create_model_and_transforms(MODEL_NAME, pretrained=PRETRAINED)
    model = model.to(device).eval()
    tokenizer = open_clip.get_tokenizer(MODEL_NAME)

    # 4. ENCODE TEXT QUERY
    print("🛰️ Vectorizing your search...")
    with torch.no_grad():
        text_tokens = tokenizer([query_text]).to(device)
        text_features = model.encode_text(text_tokens)
        # Normalize the vector
        text_features /= text_features.norm(dim=-1, keepdim=True)
        query_vector = text_features.cpu().numpy().flatten()

    # 5. CALCULATE SIMILARITY
    print("⚖️ Measuring similarity across library...")
    # Stack all vectors from the dataframe into a single matrix
    asset_vectors = np.stack(df['vector'].values)
    
    # Cosine Similarity = Dot Product (since vectors are usually pre-normalized)
    # result = asset_vectors @ query_vector
    similarities = np.dot(asset_vectors, query_vector)
    df['similarity'] = similarities

    # 6. GET BEST MATCH
    top_match = df.sort_values(by='similarity', ascending=False).iloc[0]
    best_path = os.path.normpath(top_match['path'])
    score = top_match['similarity']

    # 7. RENAME-PROOF CHECK
    if not os.path.exists(best_path):
        print(f"\n⚠️ FILE MOVED: The brain thought it was at {best_path}, but it's not there.")
        print("💡 Tip: Run index_master.py on your new folders to update the paths via MD5.")
        # We can still copy the filename so Everything Search can try to find it by name
        filename = os.path.basename(best_path)
        set_clipboard(filename)
        print(f"📋 Filename '{filename}' copied to clipboard instead.")
    else:
        print(f"\n🎯 TOP MATCH ({score:.2f} confidence):")
        print(f"📄 {os.path.basename(best_path)}")
        print(f"📂 {os.path.dirname(best_path)}")
        
        set_clipboard(best_path)
        print("\n✨ PATH COPIED TO CLIPBOARD!")
        print("👉 Go to Everything Search and press Ctrl+V.")

    # Keep window open if run via double-click
    print("\n" + "-"*30)
    input("Press Enter to close...")

if __name__ == "__main__":
    try:
        find_asset()
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        input("Press Enter to exit...")