"""Quick diagnostic: what does allowed_subcats contain for object type?"""
import sys, types, importlib.util, os

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

# Replicate the allowed_subcats build for "object"
asset_type = "object"
_type_prefix = asset_type.capitalize()   # "Object"
_all_groups = ia._kw_subcategory_groups()
_type_subcats = sorted(
    subcat for subcat, grp in _all_groups.items()
    if grp.lower().startswith(_type_prefix.lower())
)
print(f"_type_prefix = {_type_prefix!r}")
print(f"_type_subcats ({len(_type_subcats)}): {_type_subcats}")
print()

# Check if Sculpture is in there
print(f"'Sculpture' in _type_subcats: {'Sculpture' in _type_subcats}")
print()

# Show all group entries that start with "object"
print("All subcategory groups starting with 'object':")
for subcat, grp in sorted(_all_groups.items()):
    if grp.lower().startswith("object"):
        print(f"  {subcat!r} -> {grp!r}")

# Also show the raw groups dict sample
print()
print("Sample of _kw_subcategory_groups() (first 20):")
for i, (k, v) in enumerate(list(_all_groups.items())[:20]):
    print(f"  {k!r} -> {v!r}")
