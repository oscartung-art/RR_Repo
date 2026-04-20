"""
Live-simulation test for object_0 with --backend=online --enrich-mode=vision.

Simulates three realistic scenarios for what the online vision model returns:
  A) Model returns exact match:       {"subcategory": "Sculpture", ...}
  B) Model returns free-text label:   {"subcategory": "Modern Sculpture", ...}
  C) Model returns typo/compound:     {"subcategory": "ModernSculpture", ...}
  D) classify_image returns label:    vision_label = "ModernSculpture" (fallback path)
  E) Model returns nothing useful:    {} — should still resolve via vision_label hint

This validates current behavior where object subcategories are not constrained to
predefined leaves during AI enrichment.
"""
import sys, types, importlib.util, pathlib, os, json

# ── Stub heavy imports ───────────────────────────────────────────────────────
for mod_name in ("open_clip", "torch"):
    stub = types.ModuleType(mod_name)
    sys.modules[mod_name] = stub

pil_stub = types.ModuleType("PIL")
pil_image_stub = types.ModuleType("PIL.Image")
pil_stub.Image = pil_image_stub
sys.modules["PIL"] = pil_stub
sys.modules["PIL.Image"] = pil_image_stub

os.environ.setdefault("INGEST_BACKEND", "online")
os.environ.setdefault("OPENROUTER_API_KEY", "dummy")

sys.path.insert(0, r"D:\RR_Repo")
spec = importlib.util.spec_from_file_location("ingest_asset", r"D:\RR_Repo\tools\ingest_asset.py")
ia = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ia)

# Patch web search to empty (vision-only mode skips it anyway)
ia.web_search_enrich = lambda **kw: {}

from pathlib import Path
DUMMY_ARCHIVE = Path("TEMP_00000000.glb")
CRC = "DEADBEEF"

def run(vision_response: dict, vision_label: str = "", vision_only: bool = True):
    """Simulate one ingest cycle with a given vision model response."""
    source_stem = "object_0"
    asset_type = "object"

    # Patch enrich_vision_pass to return the simulated response
    ia.enrich_vision_pass = lambda *a, **kw: vision_response

    hints = ia.parse_filename_hints(source_stem)
    if vision_label:
        hints["vision_label"] = vision_label

    row = ia.build_metadata_row(
        thumbnail_filename="",
        archive_path=DUMMY_ARCHIVE,
        asset_type=asset_type,
        source_stem=source_stem,
        crc32_value=CRC,
    )
    row = ia.enrich_row_with_models(
        image_path=Path(__file__),
        source_stem=source_stem,
        asset_type=asset_type,
        hints=hints,
        row=row,
        session_context="",
        session_hints=None,
        vision_only=vision_only,
        disable_web_search=True,
    )
    return row.get("Subject", "")

passed = 0
failed = 0

def check(label, mood, expected):
    global passed, failed
    ok = mood == expected
    status = "PASS" if ok else "FAIL"
    print(f"{status}  [{label}]  Subject={mood!r}  expected={expected!r}")
    if ok:
        passed += 1
    else:
        failed += 1

# A) Exact match from vision model
check("A: exact match",
      run({"subcategory": "Sculpture", "model_name": "-", "brand": "-",
           "collection": "-", "primary_material_or_color": "-",
           "usage_location": "-", "shape_form": "-", "period": "-",
           "size": "-", "vendor_name": "-"}),
      "Object/Decor/Sculpture")

# B) Free-text is preserved (not forced into canonical leaves)
check("B: free-text 'Modern Sculpture'",
      run({"subcategory": "Modern Sculpture"}),
      "Modern Sculpture")

# C) CamelCase compound is preserved
check("C: compound 'ModernSculpture'",
      run({"subcategory": "ModernSculpture"}),
      "ModernSculpture")

# D) Vision model returns nothing useful, but classify_image gave a label
check("D: empty vision_data, vision_label='ModernSculpture'",
      run({}, vision_label="ModernSculpture"),
      "ModernSculpture")

# E) Vision model returns nothing at all
check("E: empty vision_data, no label (should be '-')",
      run({}, vision_label=""),
      "-")

print(f"\n{passed} passed, {failed} failed.")
if failed:
    sys.exit(1)
