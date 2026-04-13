"""
Offline test: verify that object_0 with vision_label="Modernscuulpture"
resolves to Mood = "Object/Decor/Sculpture" after the fix.

Runs without Ollama or OpenRouter by monkey-patching the enrichment
functions to return empty dicts (simulating no web/vision data).
"""
import sys
import types
import importlib

# ── Stub heavy imports before loading ingest_asset ──────────────────────────
for mod_name in ("open_clip", "torch"):
    stub = types.ModuleType(mod_name)
    sys.modules[mod_name] = stub

# PIL stub
pil_stub = types.ModuleType("PIL")
pil_image_stub = types.ModuleType("PIL.Image")
pil_stub.Image = pil_image_stub
sys.modules["PIL"] = pil_stub
sys.modules["PIL.Image"] = pil_image_stub

# ── Patch path constants so the script doesn't need real drives ──────────────
import os, pathlib
os.environ.setdefault("INGEST_BACKEND", "online")
os.environ.setdefault("OPENROUTER_API_KEY", "dummy")

# Temporarily redirect the KEYWORDS_MD path to the real file on the mounted drive.
# We'll patch it after import.

sys.path.insert(0, r"D:\RR_Repo")  # so ingest_asset can find Shared/ etc.

import importlib.util, pathlib as _pl

spec = importlib.util.spec_from_file_location(
    "ingest_asset",
    r"D:\RR_Repo\tools\ingest_asset.py",
)
ia = importlib.util.module_from_spec(spec)

# Patch constants before exec_module runs expensive startup code
# by overriding the module dict after creation but before exec.
# We can't do that cleanly, so we patch after load instead.
spec.loader.exec_module(ia)

# ── Monkey-patch enrichment functions to be no-ops ──────────────────────────
ia.web_search_enrich = lambda **kw: {}
ia.enrich_vision_pass = lambda *a, **kw: {}
ia.ollama_generate = lambda *a, **kw: ""

# ── Run the test ─────────────────────────────────────────────────────────────
from pathlib import Path

source_stem = "object_0"
asset_type = "object"
enrich_mode = "vision"   # object defaults to vision; but vision_data will be empty

hints = ia.parse_filename_hints(source_stem)
# Simulate vision classify returning a typo label
hints["vision_label"] = "Modernscuulpture"

# Build initial row
dummy_archive = Path("TEMP_00000000.glb")
crc = "DEADBEEF"
row = ia.build_metadata_row(
    thumbnail_filename="",
    archive_path=dummy_archive,
    asset_type=asset_type,
    source_stem=source_stem,
    crc32_value=crc,
)

# Enrich (vision_data will be empty because we patched enrich_vision_pass)
row = ia.enrich_row_with_models(
    image_path=Path("dummy.jpeg"),
    source_stem=source_stem,
    asset_type=asset_type,
    hints=hints,
    row=row,
    session_context="",
    session_hints=None,
    enrich_mode=enrich_mode,
)

mood = row.get("Mood", "")
print(f"Mood (Subcategory Path): {mood}")
assert mood == "Object/Decor/Sculpture", (
    f"FAIL: expected 'Object/Decor/Sculpture', got '{mood}'"
)
print("PASS: Sculpture resolves to Object/Decor/Sculpture")

# ── Test 2: prefix code 12-11 in filename ────────────────────────────────────
source_stem2 = "12-11 object_0"
hints2 = ia.parse_filename_hints(source_stem2)
row2 = ia.build_metadata_row(
    thumbnail_filename="",
    archive_path=dummy_archive,
    asset_type=asset_type,
    source_stem=source_stem2,
    crc32_value=crc,
)
row2 = ia.enrich_row_with_models(
    image_path=Path("dummy.jpeg"),
    source_stem=source_stem2,
    asset_type=asset_type,
    hints=hints2,
    row=row2,
    session_context="",
    session_hints=None,
    enrich_mode="text",   # text mode — prefix code should still win
)
mood2 = row2.get("Mood", "")
print(f"\nMood (prefix code 12-11, text mode): {mood2}")
assert mood2 == "Object/Decor/Sculpture", (
    f"FAIL: expected 'Object/Decor/Sculpture', got '{mood2}'"
)
print("PASS: Prefix code 12-11 resolves to Object/Decor/Sculpture in text mode")

# ── Test 3: stem contains keyword "sculpture" ─────────────────────────────────
source_stem3 = "modern_sculpture_01"
hints3 = ia.parse_filename_hints(source_stem3)
row3 = ia.build_metadata_row(
    thumbnail_filename="",
    archive_path=dummy_archive,
    asset_type=asset_type,
    source_stem=source_stem3,
    crc32_value=crc,
)
row3 = ia.enrich_row_with_models(
    image_path=Path("dummy.jpeg"),
    source_stem=source_stem3,
    asset_type=asset_type,
    hints=hints3,
    row=row3,
    session_context="",
    session_hints=None,
    enrich_mode="text",   # text mode — keyword map should fire
)
mood3 = row3.get("Mood", "")
print(f"\nMood (stem 'modern_sculpture_01', text mode): {mood3}")
assert mood3 == "Object/Decor/Sculpture", (
    f"FAIL: expected 'Object/Decor/Sculpture', got '{mood3}'"
)
print("PASS: Keyword 'sculpture' in stem resolves to Object/Decor/Sculpture in text mode")

print("\nAll tests passed.")
