#!/usr/bin/env python3
"""Simulate exactly what clipboard watcher does"""

import sys
from pathlib import Path

# Change to tools directory like clipboard watcher does
import os
os.chdir(str(Path(__file__).parent / "tools"))
sys.path.insert(0, ".")

# Now import the way clipboard watcher does
from ingest_asset import infer_metadata_fields, enrich_row_with_models, HAS_HANZICONV
from move_delete_assets import _load_efu, _write_efu, _row_basename

print("=" * 70)
print("Testing Import from Clipboard Watcher Context")
print("=" * 70)
print(f"Current directory: {os.getcwd()}")
print(f"HAS_HANZICONV: {HAS_HANZICONV}")

if HAS_HANZICONV:
    print("✓ hanziconv is available in this context")
else:
    print("✗ hanziconv is NOT available in this context")
    print("  This is the problem!")

print("\n" + "=" * 70)
print("Testing fetch_vegetation_wiki_data")
print("=" * 70)

# Import the function
from ingest_asset import fetch_vegetation_wiki_data

latin, common, chinese = fetch_vegetation_wiki_data("Zelkova_serrata")
print(f"Latin:   {latin}")
print(f"Common:  {common}")
print(f"Chinese: {chinese}")

if chinese == "櫸樹":
    print("\n✓ Traditional Chinese works!")
elif chinese == "榉树":
    print("\n✗ Simplified Chinese - conversion not working")
else:
    print(f"\n? Got: {chinese}")

print("=" * 70)
