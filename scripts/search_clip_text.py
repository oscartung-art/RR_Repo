"""
--- SCRIPT: search_clip_text.py ---
PURPOSE: Semantic search for 3D assets using a text query and CLIP (ViT-L-14).

USAGE:
	1. Make sure G:/_index.parquet exists (built by index_master.py).
	2. Run this script and enter a text description when prompted.
	3. The script encodes your text with CLIP, finds the top 10 matches, and prints their paths.

DEPENDENCIES: torch, open_clip, pandas, numpy, pywin32
"""
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
	print("--- \U0001F50D VIBE SEARCH v1.0 ---")
	if not os.path.exists(PARQUET_PATH):
		print(f"\u274c Brain not found at {PARQUET_PATH}. Please run index_master.py first.")
		return
	print("\U0001F9E0 Loading Brain into memory...")
	df = pd.read_parquet(PARQUET_PATH)
	query_text = input("\n\u2728 Describe the vibe you want: ").strip()
	if not query_text:
		return
	device = "cuda" if torch.cuda.is_available() else "cpu"
	print(f"\U0001F916 Waking up CLIP on {device.upper()}...")
	model, _, preprocess = open_clip.create_model_and_transforms(MODEL_NAME, pretrained=PRETRAINED)
	model = model.to(device).eval()
	tokenizer = open_clip.get_tokenizer(MODEL_NAME)
	print("\U0001F6F0\ufe0f Vectorizing your search...")
	with torch.no_grad():
		text_tokens = tokenizer([query_text]).to(device)
		text_features = model.encode_text(text_tokens)
		text_features /= text_features.norm(dim=-1, keepdim=True)
		query_vector = text_features.cpu().numpy().flatten()
	print("\u2696\ufe0f Measuring similarity across library...")
	asset_vectors = np.stack(df['vector'].values)
	similarities = np.dot(asset_vectors, query_vector)
	top_indices = np.argsort(similarities)[-10:][::-1]
	top_matches = df.iloc[top_indices]
	print("Top matches:")
	for path in top_matches['path']:
		print(path)

if __name__ == "__main__":
	find_asset()
