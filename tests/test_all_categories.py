from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _ingest_test_utils import DUMMY_CRC, build_enriched_row


def test_ai_subject_is_prefixed_for_supported_asset_types():
    cases = [
        ("furniture", "chair_stub", "Armchair", "Furniture/Armchair"),
        ("fixture", "lamp_stub", "Pendant Light", "Fixture/Pendant Light"),
        ("vegetation", "tree_stub", "Conifer Tree", "Vegetation/Conifer Tree"),
        ("people", "person_stub", "Standing Person", "People/Standing Person"),
        ("material", "wood_stub", "Wood Veneer", "Material/Wood Veneer"),
        ("layouts", "layout_stub", "Dining Layout", "Layouts/Dining Layout"),
        ("object", "vase_stub", "Decorative Vase", "Object/Decorative Vase"),
        ("vehicle", "car_stub", "Sports Car", "Vehicle/Sports Car"),
        ("vfx", "smoke_stub", "Smoke Plume", "VFX/Smoke Plume"),
    ]

    for asset_type, stem, ai_subject, expected_subject in cases:
        _, row = build_enriched_row(asset_type, stem, {"subject": ai_subject})
        assert row["Subject"] == expected_subject
        assert row["CRC-32"] == DUMMY_CRC
        assert "Mood" not in row


def test_material_fields_map_to_canonical_columns():
    _, row = build_enriched_row(
        "material",
        "wood-veneer-sk3-Gym-Flooring",
        {
            "subject": "Wood Veneer",
            "model_name": "SK3",
            "brand": "Loro Piana",
            "collection": "Gym Flooring",
            "primary_material_or_color": "Beige",
            "shape_form": "Linear Grain",
            "period": "Contemporary",
            "size": "1200x2400mm",
            "vendor_name": "Loro Piana",
        },
    )

    assert row["Subject"] == "Material/Wood Veneer"
    assert row["Title"] == "SK3"
    assert row["Company"] == "Loro Piana"
    assert row["Album"] == "Gym Flooring"
    assert row["Period"] == "Contemporary"
    assert row["custom_property_0"] == "Beige"
    assert row["custom_property_2"] == "Linear Grain"
    assert row["custom_property_5"] == "1200x2400mm"
    assert row["Author"] == "Loro Piana"


if __name__ == "__main__":
    test_ai_subject_is_prefixed_for_supported_asset_types()
    test_material_fields_map_to_canonical_columns()
    print("All tests passed.")
