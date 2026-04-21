"""
--- SCRIPT: search_clip_image.py ---
PURPOSE: Reverse image search for 3D assets using CLIP (ViT-L-14).

USAGE:
	1. Make sure G:/_index.parquet exists (built by index_master.py).
	2. Copy an image to the clipboard or use --image-path to specify a file.
	3. Run this script to find the top 10 visually similar assets. Results are copied to the clipboard as an Everything OR query.

DEPENDENCIES: torch, open_clip, pandas, numpy, Pillow, pywin32
"""
from __future__ import annotations

import argparse
import builtins
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

DEFAULT_INDEX_PATH = Path("G:/_index.parquet")
DEFAULT_MODEL_NAME = "ViT-L-14"
DEFAULT_PRETRAINED = "openai"
DEFAULT_TOP_K = 10
DEFAULT_PATH_COLUMN = "path"
DEFAULT_VECTOR_COLUMN = "vector"

def safe_print(*args, **kwargs):
	try:
		builtins.print(*args, **kwargs)
	except UnicodeEncodeError:
		sep = kwargs.get("sep", " ")
		end = kwargs.get("end", "\n")
		text = sep.join(str(arg) for arg in args)
		fallback = text.encode("ascii", errors="replace").decode("ascii")
		builtins.print(fallback, end=end)

print = safe_print

@dataclass(frozen=True)
class SearchConfig:
	index_path: Path = DEFAULT_INDEX_PATH
	model_name: str = DEFAULT_MODEL_NAME
	pretrained: str = DEFAULT_PRETRAINED
	top_k: int = DEFAULT_TOP_K
	path_column: str = DEFAULT_PATH_COLUMN
	vector_column: str = DEFAULT_VECTOR_COLUMN

def _import_image_grab():
	from PIL import ImageGrab
	return ImageGrab

def _import_pil_image():
	from PIL import Image
	return Image

def _import_win32clipboard():
	import win32clipboard
	return win32clipboard

def get_clipboard_image(image_grab_module=None):
	image_grab_module = image_grab_module or _import_image_grab()
	try:
		image = image_grab_module.grabclipboard()
	except Exception as exc:
		raise RuntimeError(f"Unable to access clipboard image: {exc}") from exc
	if image is None:
		raise RuntimeError("No image found in clipboard.")
	if isinstance(image, list):
		raise RuntimeError("Clipboard contains file paths, not an image.")
	return image

def set_clipboard_text(text: str, clipboard_module=None) -> None:
	clipboard_module = clipboard_module or _import_win32clipboard()
	clipboard_module.OpenClipboard()
	try:
		clipboard_module.EmptyClipboard()
		clipboard_module.SetClipboardText(text, clipboard_module.CF_UNICODETEXT)
	finally:
		clipboard_module.CloseClipboard()

def load_index(index_path: Path | str, path_column: str, vector_column: str) -> pd.DataFrame:
	parquet_path = Path(index_path)
	if not parquet_path.exists():
		raise FileNotFoundError(f"Index file not found: {parquet_path}")
	index_df = pd.read_parquet(parquet_path)
	missing_columns = [column for column in (path_column, vector_column) if column not in index_df.columns]
	if missing_columns:
		raise ValueError(f"Index is missing required columns: {', '.join(missing_columns)}")
	filtered = index_df[index_df[path_column].notna() & index_df[vector_column].notna()].copy()
	if filtered.empty:
		raise ValueError("Index contains no searchable rows.")
	return filtered

def normalize_vector(vector: Sequence[float]) -> np.ndarray:
	array = np.asarray(vector, dtype=np.float32).reshape(-1)
	if array.size == 0:
		raise ValueError("Vector is empty.")
	norm = np.linalg.norm(array)
	if norm == 0:
		raise ValueError("Vector norm is zero.")
	return array / norm

def build_vector_matrix(index_df: pd.DataFrame, vector_column: str) -> np.ndarray:
	vectors = [normalize_vector(vector) for vector in index_df[vector_column].tolist()]
	dimensions = {vector.shape[0] for vector in vectors}
	if len(dimensions) != 1:
		raise ValueError("Index vectors do not all share the same dimension.")
	return np.vstack(vectors)

def find_matches(
	query_vector: Sequence[float],
	index_df: pd.DataFrame,
	top_k: int,
	path_column: str = DEFAULT_PATH_COLUMN,
	vector_column: str = DEFAULT_VECTOR_COLUMN,
) -> pd.DataFrame:
	if top_k < 1:
		raise ValueError("top_k must be at least 1.")
	normalized_query = normalize_vector(query_vector)
	vector_matrix = build_vector_matrix(index_df, vector_column)
	if vector_matrix.shape[1] != normalized_query.shape[0]:
		raise ValueError(
			f"Vector dimension mismatch: query={normalized_query.shape[0]}, index={vector_matrix.shape[1]}"
		)
	scores = vector_matrix @ normalized_query
	limit = min(top_k, len(index_df))
	top_indices = np.argsort(scores)[-limit:][::-1]
	matches = index_df.iloc[top_indices].copy()
	matches["score"] = scores[top_indices]
	matches = matches.drop_duplicates(subset=[path_column], keep="first")
	return matches

def quote_everything_term(value: str) -> str:
	text = str(value).strip()
	if not text:
		raise ValueError("Cannot format an empty Everything search term.")
	escaped = text.replace('"', '""')
	return f'"{escaped}"'

def format_everything_or(paths: Iterable[str]) -> str:
	formatted_terms = [quote_everything_term(path) for path in paths if str(path).strip()]
	if not formatted_terms:
		raise ValueError("No match paths available to format.")
	return "|".join(formatted_terms)

def load_clip_model(model_name: str, pretrained: str):
	import open_clip
	import torch
	loaded = open_clip.create_model_and_transforms(model_name, pretrained=pretrained)
	if len(loaded) == 3:
		model, _, preprocess = loaded
	else:
		model, preprocess = loaded
	device = "cuda" if torch.cuda.is_available() else "cpu"
	model = model.to(device).eval()
	return model, preprocess, device

def encode_image(image, model, preprocess, device: str) -> np.ndarray:
	import torch
	image_tensor = preprocess(image).unsqueeze(0).to(device)
	with torch.no_grad():
		image_features = model.encode_image(image_tensor)
	if hasattr(image_features, "detach"):
		image_features = image_features.detach().cpu().numpy()
	return normalize_vector(np.asarray(image_features).reshape(-1))

def build_search_string(
	image,
	index_df: pd.DataFrame,
	model,
	preprocess,
	device: str,
	top_k: int,
	path_column: str,
	vector_column: str,
):
	query_vector = encode_image(image, model, preprocess, device)
	matches = find_matches(
		query_vector,
		index_df,
		top_k=top_k,
		path_column=path_column,
		vector_column=vector_column,
	)
	search_string = format_everything_or(matches[path_column].tolist())
	return search_string, matches

def reverse_image_search(
	config: SearchConfig,
	image=None,
	index_df: pd.DataFrame | None = None,
	model_bundle=None,
	clipboard_writer=None,
):
	image = image if image is not None else get_clipboard_image()
	index_df = index_df if index_df is not None else load_index(
		config.index_path,
		path_column=config.path_column,
		vector_column=config.vector_column,
	)
	if model_bundle is None:
		model_bundle = load_clip_model(config.model_name, config.pretrained)
	model, preprocess, device = model_bundle
	search_string, matches = build_search_string(
		image=image,
		index_df=index_df,
		model=model,
		preprocess=preprocess,
		device=device,
		top_k=config.top_k,
		path_column=config.path_column,
		vector_column=config.vector_column,
	)
	if clipboard_writer is None:
		set_clipboard_text(search_string)
	else:
		clipboard_writer(search_string)
	return search_string, matches

def parse_args(argv=None):
	parser = argparse.ArgumentParser(description="Reverse image search over G:/_index.parquet using a clipboard image.")
	parser.add_argument("--image-path", help="Optional image path. If omitted, the script reads the clipboard image.")
	parser.add_argument("--index-path", default=str(DEFAULT_INDEX_PATH), help="Path to the parquet asset index.")
	parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="How many visual matches to return.")
	parser.add_argument("--path-column", default=DEFAULT_PATH_COLUMN, help="Column containing asset paths.")
	parser.add_argument("--vector-column", default=DEFAULT_VECTOR_COLUMN, help="Column containing CLIP vectors.")
	parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME, help="CLIP model name for open_clip.")
	parser.add_argument("--pretrained", default=DEFAULT_PRETRAINED, help="Pretrained weights identifier for open_clip.")
	parser.add_argument("--dry-run", action="store_true", help="Print the Everything query without copying it to the clipboard.")
	return parser.parse_args(argv)

def main(argv=None) -> int:
	args = parse_args(argv)
	config = SearchConfig(
		index_path=Path(args.index_path),
		model_name=args.model_name,
		pretrained=args.pretrained,
		top_k=args.top_k,
		path_column=args.path_column,
		vector_column=args.vector_column,
	)
	try:
		clipboard_writer = (lambda _text: None) if args.dry_run else None
		image = None
		if args.image_path:
			image = _import_pil_image().open(args.image_path).convert("RGB")
		search_string, matches = reverse_image_search(
			config=config,
			image=image,
			clipboard_writer=clipboard_writer,
		)
	except Exception as exc:
		print(f"image_vibe failed: {exc}")
		return 1
	print(f"Found {len(matches)} matches.")
	print(search_string)
	if args.dry_run:
		print("Dry run complete. Clipboard was not modified.")
	else:
		print("Search string copied to clipboard.")
	return 0

if __name__ == "__main__":
	raise SystemExit(main())
