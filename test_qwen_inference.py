#!/usr/bin/env python3
"""Test inference on pendant image using Qwen2.5 7B."""

import os
import sys
from pathlib import Path

# Set up Python path
sys.path.insert(0, str(Path(__file__).parent / "tools"))

# Load environment
import os
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    try:
        with open(_env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key not in os.environ:
                        os.environ[key] = value
    except Exception:
        pass

# Override model to Qwen2.5 7B Instruct
os.environ["OPENROUTER_MODEL"] = "qwen/qwen2.5-7b-instruct"
print(f"Using model: {os.environ['OPENROUTER_MODEL']}")

from ingest_asset import infer_metadata_fields
from pathlib import Path

image_path = Path(r"G:\DB\sandbox\15-05 Tubular_Horizontal_Pendant_10269 - Copy.jpg")
asset_type = "fixture"  # Lighting is fixture
source_stem = image_path.stem

print(f"\nProcessing image: {image_path.name}")
print(f"Source stem: {source_stem}")
print(f"Asset type: {asset_type}")
print("\nRunning inference...\n")

metadata = infer_metadata_fields(
    asset_type=asset_type,
    source_stem=source_stem,
    image_path=image_path
)

print("\n" + "=" * 80)
print("INFERRED METADATA:")
print("=" * 80)

import json
print(json.dumps(metadata, indent=2))
