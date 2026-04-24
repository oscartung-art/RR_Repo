#!/usr/bin/env python3
"""Test exact user input"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "tools"))

from clipboard_asset_watcher import parse_command, _looks_like_command

# Exact string the user is copying
test_input = '"G:\\DB\\sandbox\\.metadata.efu" audit:'

print("=" * 70)
print("Testing Exact User Input")
print("=" * 70)
print(f"Input: {test_input}")
print(f"Length: {len(test_input)}")
print(f"Repr: {repr(test_input)}")
print()

# Test if it looks like a command
looks_like = _looks_like_command(test_input)
print(f"Looks like command: {looks_like}")

if looks_like:
    # Parse it
    parsed = parse_command(test_input)
    print(f"Parsed result: {parsed}")
    
    if parsed is not None:
        paths, action, args = parsed
        print(f"  Paths: {paths}")
        print(f"  Action: {action}")
        print(f"  Args: {args}")
        
        if paths:
            for i, p in enumerate(paths):
                print(f"\n  Path {i+1}:")
                print(f"    String: {p}")
                print(f"    Absolute: {p.absolute()}")
                print(f"    Exists: {p.exists()}")
                print(f"    Name: {p.name}")
    else:
        print("  ✗ Parsed as None")
else:
    print("  ✗ Not recognized as command")

print("\n" + "=" * 70)
