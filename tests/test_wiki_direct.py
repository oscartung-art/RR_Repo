#!/usr/bin/env python3
"""Direct test of the fetch_vegetation_wiki_data function"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "tools"))

from ingest_asset import fetch_vegetation_wiki_data, extract_botanical_name_from_stem

print("=" * 70)
print("Testing Wikipedia Botanical Data Fetching")
print("=" * 70)

# Test 1: Direct botanical name
test_stems = [
    "Zelkova_serrata",
    "14-24 MT_PM_V40_Zelkova_serrata_01_06",
    "Acer_truncatum",
    "Acer_palmatum",
]

for stem in test_stems:
    print(f"\nTest stem: {stem}")
    
    # Extract botanical name if needed
    botanical = extract_botanical_name_from_stem(stem)
    print(f"  Extracted botanical name: {botanical}")
    
    # Fetch from Wikipedia
    latin, common, chinese = fetch_vegetation_wiki_data(botanical)
    
    print(f"  Results:")
    print(f"    Latin name:   {latin}")
    print(f"    Common name:  {common}")
    print(f"    Chinese name: {chinese}")
    print("-" * 70)

print("\n" + "=" * 70)
