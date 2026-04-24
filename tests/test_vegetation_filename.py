#!/usr/bin/env python3
"""Test vegetation enrichment Filename field fix"""

import sys
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent / "tools"))

from watcher import _enrich_image
from move_delete_assets import _load_efu

# Test file
test_image = Path("G:/DB/sandbox/14-24 MT_PM_V48_Acer_truncatum_01_06.jpg")
efu_path = test_image.parent / ".metadata.efu"

print("=" * 70)
print("Testing Vegetation Enrichment - Filename Field Fix")
print("=" * 70)
print(f"Test image: {test_image}")
print(f"Exists: {test_image.exists()}")
print()

if not test_image.exists():
    print("✗ Test image not found!")
    sys.exit(1)

# Count rows before
rows_before = 0
if efu_path.exists():
    _, rows = _load_efu(efu_path)
    rows_before = len(rows)
    print(f"EFU rows before: {rows_before}")
else:
    print(f"EFU does not exist yet")

print("\nRunning enrichment...")
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
print(f"EFU rows after: {len(rows)}")

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
print("VERIFICATION RESULTS")
print("=" * 70)

# Check critical fields
filename = target_row.get("Filename", "")
subject = target_row.get("custom_property_0", "")
common_name = target_row.get("custom_property_1", "")
chinese_name = target_row.get("custom_property_3", "")
latin_name = target_row.get("custom_property_4", "")

print(f"Filename:     {filename}")
print(f"Subject:      {subject}")
print(f"Common name:  {common_name}")
print(f"Chinese name: {chinese_name}")
print(f"Latin name:   {latin_name}")
print()

# Verify Filename is populated
if filename and filename.strip():
    print("✓ PASS: Filename field is populated!")
    print(f"  Value: '{filename}'")
else:
    print("✗ FAIL: Filename field is EMPTY!")
    sys.exit(1)

# Verify it matches the actual filename
if filename.lower() == target_name.lower():
    print("✓ PASS: Filename matches image name!")
else:
    print(f"⚠ WARNING: Filename mismatch!")
    print(f"  Expected: {target_name}")
    print(f"  Got:      {filename}")

print("\n" + "=" * 70)
print("✓ ALL TESTS PASSED - Filename field fix is working!")
print("=" * 70)
