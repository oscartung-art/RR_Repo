from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INGEST_PATH = REPO_ROOT / "tools" / "ingest_asset.py"
DUMMY_ARCHIVE = Path("TEMP_00000000.glb")
DUMMY_CRC = "DEADBEEF"


def load_ingest_asset():
    for mod_name in ("open_clip", "torch"):
        sys.modules.setdefault(mod_name, types.ModuleType(mod_name))

    if "PIL" not in sys.modules:
        pil_stub = types.ModuleType("PIL")
        pil_image_stub = types.ModuleType("PIL.Image")
        pil_stub.Image = pil_image_stub
        sys.modules["PIL"] = pil_stub
        sys.modules["PIL.Image"] = pil_image_stub

    os.environ.setdefault("INGEST_BACKEND", "online")
    os.environ.setdefault("OPENROUTER_API_KEY", "dummy")

    module_name = "ingest_asset_under_test"
    spec = importlib.util.spec_from_file_location(module_name, str(INGEST_PATH))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    module.lookup_current_db = lambda _source_stem: {}
    return module


def build_enriched_row(asset_type: str, source_stem: str, fields: dict[str, str]):
    ia = load_ingest_asset()
    ia.infer_metadata_fields = lambda **kwargs: dict(fields)
    hints = ia.parse_filename_hints(source_stem)
    row = ia.build_metadata_row(
        thumbnail_filename="",
        archive_path=DUMMY_ARCHIVE,
        asset_type=asset_type,
        source_stem=source_stem,
        crc32_value=DUMMY_CRC,
    )
    row = ia.enrich_row_with_models(
        image_path=INGEST_PATH,
        source_stem=source_stem,
        asset_type=asset_type,
        hints=hints,
        row=row,
        session_context="",
        session_hints=None,
    )
    return ia, row
