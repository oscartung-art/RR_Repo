#!/usr/bin/env python3
"""Test auto asset-type detection and Traditional Chinese"""

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
print("Testing Auto Asset-Type Detection + Traditional Chinese")
print("=" * 70)
print(f"Test image: {test_image}")
print(f"File exists: {test_image.exists()}")
print()

if not test_image.exists():
    print("✗ Test image not found!")
    sys.exit(1)

# Check if row already exists
if efu_path.exists():
    fieldnames, rows = _load_efu(efu_path)
    target_name = test_image.name
    existing_row = None
    for row in rows:
        if row.get("Filename", "").lower() == target_name.lower():
            existing_row = row
            break
    
    if existing_row:
        subject = existing_row.get("custom_property_0", "")
        print(f"Existing row found!")
        print(f"  Subject: {subject}")
        if "/" in subject:
            detected_type = subject.split("/")[0].strip().lower()
            print(f"  Expected auto-detected type: {detected_type}")
    else:
        print("No existing row found")
else:
    print("EFU file does not exist")

print("\n" + "=" * 70)
print("Running enrichment WITHOUT specifying asset type...")
print("(Should auto-detect as 'vegetation' from existing row)")
print("=" * 70)

# Run enrichment WITHOUT asset type parameter
success = _enrich_image(test_image, asset_type=None)

print("-" * 70)
print(f"\nEnrichment result: {'✓ SUCCESS' if success else '✗ FAILED'}")

if not success:
    print("✗ Enrichment failed!")
    sys.exit(1)

# Check the result
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
print("FINAL RESULTS")
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
print(f"Chinese name: {chinese_name} ← Should be Traditional!")
print(f"Latin name:   {latin_name}")
print(f"Size:         {size}")
print()

# Verify
print("=" * 70)
print("VERIFICATION")
print("=" * 70)

if chinese_name == "櫸樹":
    print(f"✓ PASS: Traditional Chinese correct: '{chinese_name}'")
elif chinese_name == "榉树":
    print(f"✗ FAIL: Got Simplified Chinese: '{chinese_name}' (expected 櫸樹)")
else:
    print(f"? UNKNOWN: Got: '{chinese_name}'")

if common_name == "Japanese Zelkova":
    print(f"✓ PASS: Common name correct: '{common_name}'")
else:
    print(f"⚠ Got: '{common_name}' (expected Japanese Zelkova)")

if latin_name == "Zelkova serrata":
    print(f"✓ PASS: Latin name correct: '{latin_name}'")
else:
    print(f"⚠ Got: '{latin_name}' (expected Zelkova serrata)")

print("\n" + "=" * 70)
print("✓ Test Complete!")
print("=" * 70)
