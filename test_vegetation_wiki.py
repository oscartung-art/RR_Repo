"""
Test vegetation Wikipedia integration after rolling back Google APIs.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "tools"))

from ingest_asset import (
    extract_botanical_name_from_stem,
    fetch_vegetation_wiki_data,
)

def test_zelkova():
    """Test Zelkova serrata extraction and Wikipedia lookup."""
    filename = "14-24 MT_PM_V40_Zelkova_serrata_01_06.jpg"
    stem = Path(filename).stem
    
    print(f"Testing: {filename}")
    print(f"Stem: {stem}")
    print()
    
    # Test botanical name extraction
    botanical = extract_botanical_name_from_stem(stem)
    print(f"Extracted botanical name: {botanical}")
    print()
    
    # Test Wikipedia lookup
    latin, common, chinese = fetch_vegetation_wiki_data(botanical)
    
    print("═══════════════════════════════════════")
    print("Wikipedia Lookup Results:")
    print("═══════════════════════════════════════")
    print(f"Latin name:   {latin}")
    print(f"Common name:  {common}")
    print(f"Chinese name: {chinese}")
    print("═══════════════════════════════════════")
    print()
    
    # Validate
    assert latin == "Zelkova serrata", f"Expected 'Zelkova serrata', got '{latin}'"
    assert common == "Japanese Zelkova", f"Expected 'Japanese Zelkova', got '{common}'"
    assert chinese == "櫸樹", f"Expected '櫸樹' (Traditional), got '{chinese}'"
    
    print("✓ All tests passed!")
    return True

if __name__ == "__main__":
    test_zelkova()
