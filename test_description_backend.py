#!/usr/bin/env python3
"""Test script to verify description-based enrichment backend."""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tools.watcher import _is_single_image_path, _looks_like_description


def test_is_single_image_path():
    """Test _is_single_image_path function."""
    test_cases = [
        ("C:\\images\\chair.jpg", True),
        ('"C:\\images\\sofa.png"', True),
        ("D:/path/to/image.jpeg", True),
        ("g:\\db\\asset.jpg", True),
        ("not an image.txt", False),
        ("image with space.jpg", True),
        ("path/to/folder", False),
        ("https://example.com/image.jpg", False),
        ("g:/db/asset.jpg enrich", False),
        ("12345", False),
    ]

    print("=== Testing _is_single_image_path ===")
    all_passed = True
    for test_str, expected in test_cases:
        result = _is_single_image_path(test_str)
        status = "✅" if result == expected else "❌"
        if result != expected:
            all_passed = False
        print(f"{status} {repr(test_str)} -> {result} (expected {expected})")

    return all_passed


def test_looks_like_description():
    """Test _looks_like_description function."""
    test_cases = [
        ("The armchair and ottoman set shown in the image is the Cream swivel chair, designed by Studio Truly Truly for Leolux LX. Also referred to in some professional catalogs as the LXR10, it is characterized by its fluid, wraparound wooden shell and high level of customization.", True),
        ("This is a very short text.", False),
        ("C:\\images\\chair.jpg", False),
        ("path/to/image.png", False),
        ("image.jpg enrich furniture", False),
        ("g:/db/asset.jpg describe", False),
        ("Product dimensions: 77 cm to 80 cm in width, 90 cm to 92 cm in depth, and 110 cm in height", True),
        ("Materials: wooden shell available in oak or walnut, upholstery in various fabrics or leathers. Base: aluminum swivel base.", True),
        ("Features: tilt mechanism and adjustable headrest.", True),
        ("Brand: Leolux LX, Model: LXR10.", True),
    ]

    print("\n=== Testing _looks_like_description ===")
    all_passed = True
    for test_str, expected in test_cases:
        result = _looks_like_description(test_str)
        status = "✅" if result == expected else "❌"
        if result != expected:
            all_passed = False
        truncated = test_str[:100] + '...' if len(test_str) > 100 else test_str
        print(f"{status} {repr(truncated)} -> {result} (expected {expected})")

    return all_passed


def test_with_sample_data():
    """Test with a real image if available."""
    print("\n=== Testing with real image ===")

    # Look for test images in sandbox
    sandbox_dir = Path(r"G:\DB\sandbox")
    if not sandbox_dir.exists():
        print("⚠ No test images found")
        return False

    # Find any jpg/png in sandbox
    test_images = list(sandbox_dir.glob("*.jpg")) + list(sandbox_dir.glob("*.png"))
    if not test_images:
        print("⚠ No test images found")
        return False

    # Try the first image
    test_image = test_images[0]

    print(f"Using test image: {test_image.name}")

    # Create a sample description
    sample_description = """The armchair and ottoman set shown in the image is the Cream swivel chair, designed by Studio Truly Truly for Leolux LX.
Also referred to in some professional catalogs as the LXR10, it is characterized by its fluid, wraparound wooden shell and high level of customization.

Key Features and Specifications:
- Design Concept: Single, fluid form that bends and folds for luxurious seating
- Materials: Curved wooden shell (oak or walnut), fabric/leather upholstery
- Base: Four-star aluminum swivel base (polished aluminum or epoxy colors)
- Functions: Tilt mechanism and adjustable headrest
- Dimensions: Approximately 77-80 cm width, 90-92 cm depth, 110 cm height"""

    print("Sample description prepared")

    # Describe handler removed in watcher; skip this test
    print("Describe handler removed; skipping describe enrichment test")
    return True


def run_all_tests():
    """Run all tests."""
    print("Running all tests for description-based enrichment backend")
    print("=" * 80)

    test1 = test_is_single_image_path()
    test2 = test_looks_like_description()
    test3 = test_with_sample_data()

    print("\n" + "=" * 80)

    if test1 and test2 and test3:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")


if __name__ == "__main__":
    run_all_tests()
