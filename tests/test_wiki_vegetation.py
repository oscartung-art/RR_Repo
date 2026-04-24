#!/usr/bin/env python3
"""Test Wikipedia botanical name enrichment for Zelkova_serrata"""

import sys
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent / "tools"))

from clipboard_asset_watcher import _enrich_image
from move_delete_assets import _load_efu

# Test file
test_image = Path("G:/DB/sandbox/14-24 MT_PM_V40_Zelkova_serrata_01_06.jpg")
efu_path = test_image.parent / ".metadata.efu"

print("=" * 70)
print("Testing Wikipedia Botanical Name Enrichment")
print("=" * 70)
print(f"Test image: {test_image}")
print(f"Expected stem: Zelkova_serrata")
print(f"File exists: {test_image.exists()}")
print()

if not test_image.exists():
    print("✗ Test image not found!")
    sys.exit(1)

print("\nRunning enrichment with Wikipedia lookup...")
print("-" * 70)

# Run enrichment
success = _enrich_image(test_image, "vegetation")

print("-" * 70)
print(f"\nEnrichment result: {'✓ SUCCESS' if success else '✗ FAILED'}")

if not success:
    print("✗ Enrichment failed!")
    sys.exit(1)

# Check the result
if not efu_path.exists():
    print("✗ EFU file was not created!")
    sys.exit(1)

fieldnames, rows = _load_efu(efu_path)

# Find the row for our test image
target_name = test_image.name
target_row = None
for row in rows:
    if row.get("Filename", "").lower() == target_name.lower():
        target_row = row
        break

if not target_row:
    print(f"✗ Row not found for {target_name}")
    sys.exit(1)

print(f"\n{'=' * 70}")
print("BOTANICAL NAMES RETRIEVED")
print("=" * 70)

# Check botanical fields
filename = target_row.get("Filename", "")
subject = target_row.get("custom_property_0", "")
common_name = target_row.get("custom_property_1", "")
shape = target_row.get("custom_property_3", "")
chinese_name = target_row.get("custom_property_4", "")
latin_name = target_row.get("custom_property_5", "")
size = target_row.get("custom_property_6", "")

print(f"Filename:     {filename}")
print(f"Subject:      {subject}")
print(f"Common name:  {common_name}")
print(f"Shape:        {shape}")
print(f"Chinese name: {chinese_name}")
print(f"Latin name:   {latin_name}")
print(f"Size:         {size}")
print()

# Verify names are not empty
print("=" * 70)
print("VERIFICATION")
print("=" * 70)

if common_name and common_name != "-":
    print(f"✓ Common name populated: '{common_name}'")
else:
    print("✗ Common name is empty or '-'")

if chinese_name and chinese_name != "-":
    print(f"✓ Chinese name populated: '{chinese_name}'")
else:
    print("✗ Chinese name is empty or '-'")

if latin_name and latin_name != "-":
    print(f"✓ Latin name populated: '{latin_name}'")
else:
    print("✗ Latin name is empty or '-'")

print("\n" + "=" * 70)
print("Expected Results from Wikipedia:")
print("  Common name: Japanese Zelkova")
print("  Latin name:  Zelkova Serrata")
print("  Chinese name: 櫸樹 (or similar)")
print("=" * 70)
