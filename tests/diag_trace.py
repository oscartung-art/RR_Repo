"""
Trace test: monkey-patch enrich_row_with_models to add debug prints
at the exact point where _obj_subcat is computed.
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

# Wrap enrich_row_with_models to inject tracing
_orig = ia.enrich_row_with_models

def _traced(*args, **kwargs):
    # Inject a debug hook by temporarily patching build_mood_hierarchy
    _orig_bmh = ia.build_mood_hierarchy
    def _bmh_debug(subcat):
        print(f"  [TRACE] build_mood_hierarchy called with subcat={subcat!r}")
        result = _orig_bmh(subcat)
        print(f"  [TRACE] -> {result!r}")
        return result
    ia.build_mood_hierarchy = _bmh_debug
    try:
        return _orig(*args, **kwargs)
    finally:
        ia.build_mood_hierarchy = _orig_bmh

ia.enrich_row_with_models = _traced

from pathlib import Path
source_stem = "object_0"
asset_type = "object"
hints = ia.parse_filename_hints(source_stem)

row = ia.build_metadata_row(
    thumbnail_filename="",
    archive_path=Path("TEMP.glb"),
    asset_type=asset_type,
    source_stem=source_stem,
    crc32_value="DEAD",
)

print("=== Calling enrich_row_with_models ===")
row = ia.enrich_row_with_models(
    image_path=Path("dummy.jpeg"),
    source_stem=source_stem,
    asset_type=asset_type,
    hints=hints,
    row=row,
    session_context="",
    session_hints=None,
    enrich_mode="vision",
)
print(f"\nFinal Mood = {row.get('Mood')!r}")
