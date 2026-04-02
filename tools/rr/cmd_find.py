"""
cmd_find.py — rr find [query | image_path]

Semantic asset search using CLIP + _index.parquet.
Supports text queries and image-based queries.

Examples:
    rr find "Modern Eames Chair"
    rr find "G:/ref/client_photo.jpg"
    rr find "warm wood texture" --top 20
    rr find --stats

Requires:
    pip install torch transformers pandas pyarrow pillow
    _index.parquet must exist at G:/_index.parquet
    CLIP ViT-L/14 model (auto-downloaded on first run, ~4.5 GB)
"""

import sys
import os
import subprocess
import tempfile
from pathlib import Path
from .utils import c, REPO_ROOT

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
from Shared.config import ASSET_ROOT

INDEX_PATH      = ASSET_ROOT / "_index.parquet"
CLIP_MODEL_ID   = "openai/clip-vit-large-patch14"
EFU_TEMP_PATH   = Path(tempfile.gettempdir()) / "rr_find_results.efu"
EVERYTHING_EXE  = Path("C:/Program Files/Everything/Everything.exe")

DEFAULT_TOP_N   = 10


# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------
def _check_deps():
    """Return True if all required packages are available."""
    missing = []
    for pkg in ("torch", "transformers", "pandas", "pyarrow", "PIL"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg if pkg != "PIL" else "pillow")
    return missing


# ---------------------------------------------------------------------------
# Index stats
# ---------------------------------------------------------------------------
def _show_stats():
    if not INDEX_PATH.exists():
        print(c("red", f"Index not found: {INDEX_PATH}"))
        print(c("grey", "  Run 'python scripts/index_assets.py' to build it."))
        return
    import pandas as pd
    df = pd.read_parquet(INDEX_PATH, columns=["path", "rating"])
    total   = len(df)
    rated   = df["rating"].notna().sum()
    unrated = total - rated
    print(f"\n{c('cyan', '=== _index.parquet Stats ===')}")
    print(f"  {c('white', 'Total assets:')}  {total:,}")
    print(f"  {c('green_fg', 'Rated:')}         {int(rated):,}")
    print(f"  {c('grey', 'Unrated:')}       {unrated:,}")
    print(f"  {c('grey', 'Index path:')}    {INDEX_PATH}\n")


# ---------------------------------------------------------------------------
# EFU export + Everything Search launch
# ---------------------------------------------------------------------------
def _open_in_everything(paths):
    """Write an EFU file and open it in Everything Search."""
    lines = ["Filename,Size,Date Modified,Date Created,Attributes"]
    for p in paths:
        fp = Path(p)
        lines.append(f"{fp},,,,")
    EFU_TEMP_PATH.write_text("\n".join(lines), encoding="utf-8")

    if EVERYTHING_EXE.exists():
        subprocess.Popen([str(EVERYTHING_EXE), "-open", str(EFU_TEMP_PATH)])
        print(c("green_fg", f"  Opened {len(paths)} results in Everything Search."))
    else:
        print(c("yellow", f"  Everything Search not found at {EVERYTHING_EXE}"))
        print(c("grey",   f"  EFU saved to: {EFU_TEMP_PATH}"))


# ---------------------------------------------------------------------------
# Core search
# ---------------------------------------------------------------------------
def _search(query, top_n, is_image=False):
    missing = _check_deps()
    if missing:
        print(c("red", f"Missing packages: {', '.join(missing)}"))
        print(c("grey", f"  Run: pip install {' '.join(missing)}"))
        return

    import torch
    import pandas as pd
    import numpy as np
    from transformers import CLIPProcessor, CLIPModel

    # --- Load index ---
    if not INDEX_PATH.exists():
        print(c("red", f"Index not found: {INDEX_PATH}"))
        print(c("grey", "  Run 'python scripts/index_assets.py' to build it first."))
        print(c("grey", "  Or run 'python scripts/audit_library.py' to check asset pairs."))
        return

    print(c("grey", "  Loading index..."), end=" ", flush=True)
    df = pd.read_parquet(INDEX_PATH)
    if "vector" not in df.columns:
        print(c("red", "\n  Index has no 'vector' column. Re-run index_assets.py."))
        return

    vectors = np.stack(df["vector"].values).astype("float32")
    print(c("green_fg", f"OK ({len(df):,} assets)"))

    # --- Load CLIP model ---
    print(c("grey", "  Loading CLIP model..."), end=" ", flush=True)
    device    = "cuda" if torch.cuda.is_available() else "cpu"
    model     = CLIPModel.from_pretrained(CLIP_MODEL_ID).to(device)
    processor = CLIPProcessor.from_pretrained(CLIP_MODEL_ID)
    print(c("green_fg", f"OK ({device.upper()})"))

    # --- Encode query ---
    with torch.no_grad():
        if is_image:
            from PIL import Image
            img    = Image.open(query).convert("RGB")
            inputs = processor(images=img, return_tensors="pt").to(device)
            q_vec  = model.get_image_features(**inputs)
        else:
            inputs = processor(text=[query], return_tensors="pt", padding=True).to(device)
            q_vec  = model.get_text_features(**inputs)

    q_vec = q_vec.cpu().numpy().astype("float32")
    q_vec /= np.linalg.norm(q_vec)

    # --- Cosine similarity ---
    norms   = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms   = np.where(norms == 0, 1, norms)
    normed  = vectors / norms
    scores  = normed @ q_vec.T
    scores  = scores.flatten()

    top_idx = scores.argsort()[::-1][:top_n]

    # --- Display results ---
    label = f"Image: {Path(query).name}" if is_image else f'"{query}"'
    print(f"\n{c('cyan', f'=== Top {top_n} results for {label} ===')}\n")
    result_paths = []
    for rank, i in enumerate(top_idx, 1):
        row     = df.iloc[i]
        score   = scores[i]
        path    = row["path"]
        rating  = row.get("rating", "")
        rating_str = f"  {'★' * int(rating)}" if rating and str(rating).isdigit() else ""
        print(f"  {c('yellow', f'{rank:>2}.')} {c('white', f'{score:.3f}')}  {path}{c('green_fg', rating_str)}")
        result_paths.append(path)

    print()
    _open_in_everything(result_paths)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def run(args):
    if not args:
        print(c("red", "Usage: rr find [query | image_path] [--top N] [--stats]"))
        print(c("grey", '  Example: rr find "Modern Eames Chair"'))
        print(c("grey", '  Example: rr find "G:/ref/photo.jpg"'))
        print(c("grey", '  Example: rr find --stats'))
        return

    if args[0] == "--stats":
        _show_stats()
        return

    # Parse --top N flag
    top_n = DEFAULT_TOP_N
    query_parts = []
    i = 0
    while i < len(args):
        if args[i] == "--top" and i + 1 < len(args):
            try:
                top_n = int(args[i + 1])
                i += 2
                continue
            except ValueError:
                pass
        query_parts.append(args[i])
        i += 1

    query = " ".join(query_parts)

    # Detect image path
    is_image = False
    query_path = Path(query)
    if query_path.exists() and query_path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
        is_image = True
    elif query.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        print(c("yellow", f"  Image path not found: {query}"))
        print(c("grey",   "  Falling back to text search."))

    _search(query, top_n, is_image=is_image)
