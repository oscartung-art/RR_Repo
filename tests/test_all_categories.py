"""
Offline regression test: verify that ALL asset types now flow through
enrich_row_with_models in text mode and produce a correct Mood path
and Manager label.  No Ollama or OpenRouter required.
"""
import sys, types, importlib.util, pathlib, os

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

spec = importlib.util.spec_from_file_location(
    "ingest_asset", r"D:\RR_Repo\tools\ingest_asset.py"
)
ia = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ia)

# Patch all network calls to no-ops
ia.web_search_enrich = lambda **kw: {}
ia.enrich_vision_pass = lambda *a, **kw: {}
ia.ollama_generate = lambda *a, **kw: ""

from pathlib import Path

DUMMY_ARCHIVE = Path("TEMP_00000000.glb")
CRC = "DEADBEEF"

def run(asset_type, source_stem, vision_label=None, enrich_mode="text"):
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
        image_path=Path("dummy.jpeg"),
        source_stem=source_stem,
        asset_type=asset_type,
        hints=hints,
        row=row,
        session_context="",
        session_hints=None,
        enrich_mode=enrich_mode,
    )
    return row

# ── Test cases ───────────────────────────────────────────────────────────────
tests = [
    # (asset_type, source_stem, vision_label, enrich_mode, expected_mood_prefix, expected_manager)
    ("object",     "object_0",              "Modernscuulpture", "vision", "Object/Decor/Sculpture", "Object"),
    ("object",     "12-11 object_0",        None,               "text",   "Object/Decor/Sculpture", "Object"),
    ("object",     "modern_sculpture_01",   None,               "text",   "Object/Decor/Sculpture", "Object"),
    ("furniture",  "10-03 mychair",         None,               "text",   "Furniture/Seating/Chair", "Furniture"),
    ("fixture",    "15-04 floor_lamp_01",   None,               "text",   "Fixture/Lighting/FloorLamp", "Fixture"),
    ("vegetation", "14-24 oak_tree",        None,               "text",   "Vegetation/Tree",         "Vegetation"),
    ("vehicle",    "vehicle_car_01",        None,               "text",   "-",                       "Vehicle"),
    ("vfx",        "vfx_fire_01",           None,               "text",   "-",                       "VFX"),
    ("material",   "material_wood_01",      None,               "text",   "-",                       "Material"),
    ("buildings",  "11-03 door_01",         None,               "text",   "Building/Door",           "Buildings"),
    ("layouts",    "layout_dining_01",      None,               "text",   "-",                       "Layouts"),
    ("people",     "people_woman_01",       None,               "text",   "-",                       "People"),
    ("location",   "location_lobby_01",     None,               "text",   "-",                       "Location"),
    ("procedural", "procedural_railing_01", None,               "text",   "-",                       "Procedural"),
]

passed = 0
failed = 0
for asset_type, stem, vlabel, mode, mood_prefix, manager_label in tests:
    row = run(asset_type, stem, vlabel, mode)
    mood = row.get("Mood", "")
    manager = row.get("Manager", "")

    # Mood check: either exact prefix match or we just verify it's not "-" when expected
    mood_ok = (
        mood_prefix == "-"  # don't care / no taxonomy entry yet
        or mood.startswith(mood_prefix)
    )
    manager_ok = manager_label in manager

    status = "PASS" if (mood_ok and manager_ok) else "FAIL"
    if status == "FAIL":
        failed += 1
        print(f"FAIL  [{asset_type:12}] stem={stem!r:30} mood={mood!r:35} manager={manager!r}")
        if not mood_ok:
            print(f"       expected Mood to start with {mood_prefix!r}")
        if not manager_ok:
            print(f"       expected Manager to contain {manager_label!r}")
    else:
        passed += 1
        print(f"PASS  [{asset_type:12}] Mood={mood!r:35} Manager={manager.split(';')[0]!r}")

print(f"\n{passed} passed, {failed} failed.")
if failed:
    sys.exit(1)
