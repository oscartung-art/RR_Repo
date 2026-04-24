#!/usr/bin/env python3
"""Check if HAS_HANZICONV is set correctly in ingest_asset module"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "tools"))

# Force reload to get fresh module
if 'ingest_asset' in sys.modules:
    del sys.modules['ingest_asset']

import ingest_asset

print("=" * 70)
print("Checking HAS_HANZICONV flag in ingest_asset.py")
print("=" * 70)
print(f"HAS_HANZICONV: {ingest_asset.HAS_HANZICONV}")

if ingest_asset.HAS_HANZICONV:
    print("✓ hanziconv is available")
    
    # Test the conversion directly
    test_simplified = "榉树"
    test_traditional = ingest_asset.HanziConv.toTraditional(test_simplified)
    print(f"\nTest conversion:")
    print(f"  Simplified:  {test_simplified}")
    print(f"  Traditional: {test_traditional}")
    
    # Now test the actual function
    print("\n" + "=" * 70)
    print("Testing fetch_vegetation_wiki_data function")
    print("=" * 70)
    
    latin, common, chinese = ingest_asset.fetch_vegetation_wiki_data("Zelkova_serrata")
    print(f"Latin:   {latin}")
    print(f"Common:  {common}")
    print(f"Chinese: {chinese}")
    
    if chinese == "櫸樹":
        print("\n✓ SUCCESS: Traditional Chinese is correct!")
    elif chinese == "榉树":
        print("\n✗ FAIL: Still getting Simplified Chinese")
    else:
        print(f"\n? Got: {chinese}")
else:
    print("✗ hanziconv is NOT available")
    print("  Run: pip install hanziconv")

print("\n" + "=" * 70)
