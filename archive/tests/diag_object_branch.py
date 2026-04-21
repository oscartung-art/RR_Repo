"""
Debug: trace the exact values inside the object branch of enrich_row_with_models
when vision_data = {"subcategory": "Sculpture"}.
"""
import sys, types, importlib.util, os, re, difflib

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

ia.web_search_enrich = lambda **kw: {}
ia.enrich_vision_pass = lambda *a, **kw: {"subcategory": "Sculpture"}

from pathlib import Path

source_stem = "object_0"
asset_type = "object"
hints = ia.parse_filename_hints(source_stem)

# Replicate allowed_subcats build
_type_prefix = asset_type.capitalize()
_all_groups = ia._kw_subcategory_groups()
_type_subcats = sorted(
    subcat for subcat, grp in _all_groups.items()
    if grp.lower().startswith(_type_prefix.lower())
)
allowed_subcats = _type_subcats if _type_subcats else sorted(_all_groups.keys())
print(f"allowed_subcats has {len(allowed_subcats)} entries")
print(f"'Sculpture' in allowed_subcats: {'Sculpture' in allowed_subcats}")

# Simulate the vision_data
vision_data = {"subcategory": "Sculpture"}

# Replicate _raw_subcat
raw_from_vision = vision_data.get("subcategory", "")
print(f"\nvision_data['subcategory'] = {raw_from_vision!r}")

clean_raw = ia.clean_display_case(raw_from_vision.strip())
print(f"clean_display_case result = {clean_raw!r}")

# Now simulate _match_allowlist
raw = clean_raw
print(f"\n--- _match_allowlist({raw!r}) ---")
if not raw or raw == "-":
    print("  -> early return: empty/dash")
elif raw in allowed_subcats:
    print(f"  -> exact match: {raw!r}")
else:
    raw_spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", raw).lower()
    raw_norm = re.sub(r"[^a-z0-9]+", "", raw_spaced)
    raw_dedup = re.sub(r"(.)\1+", r"\1", raw_norm)
    print(f"  raw_spaced={raw_spaced!r}  raw_norm={raw_norm!r}  raw_dedup={raw_dedup!r}")
    best = ""
    for subcat in allowed_subcats:
        sub_norm = re.sub(r"[^a-z0-9]+", "", subcat.lower())
        if sub_norm and (sub_norm in raw_norm or sub_norm in raw_dedup):
            if len(subcat) > len(best):
                best = subcat
    print(f"  substring best={best!r}")

# Check clean_display_case behavior on "Sculpture"
print(f"\nclean_display_case('Sculpture') = {ia.clean_display_case('Sculpture')!r}")
print(f"clean_display_case('sculpture') = {ia.clean_display_case('sculpture')!r}")
print(f"'Sculpture' == clean_display_case('Sculpture'): {'Sculpture' == ia.clean_display_case('Sculpture')}")
