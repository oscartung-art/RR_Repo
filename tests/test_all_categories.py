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
        assert row["custom_property_0"] == expected_subject
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

    # New mapping semantic meanings:
    # custom_property_0 = Subject (Primary asset classification)
    # custom_property_1 = Title (Model name/designer name)
    # custom_property_2 = Company (Brand/Designer/Collection identifier)
    # custom_property_3 = Album (Style or era classification)
    # custom_property_4 = Author (Primary color/material/surface finish)
    # custom_property_5 = Period (Usage context/location)
    # custom_property_6 = Color (Shape/physical configuration)
    # custom_property_7 = Location (Dimensions/scale classification)
    assert row["custom_property_0"] == "Material/Wood Veneer"
    assert row["custom_property_1"] == "SK3"
    assert row["custom_property_2"] == "Loro Piana"
    assert row["custom_property_3"] == "Contemporary"  # period = style/era → now in cp3 (Album slot)
    assert row["custom_property_5"] == "-"  # usage_location not provided in this test
    assert row["custom_property_4"] == "Beige"  # primary color → cp4 (Author slot)
    assert row["custom_property_6"] == "Linear Grain"  # shape/form → cp6 (Color slot)
    assert row["custom_property_7"] == "1200x2400mm"  # dimensions → cp7 (Location slot)


if __name__ == "__main__":
    test_ai_subject_is_prefixed_for_supported_asset_types()
    test_material_fields_map_to_canonical_columns()
    print("All tests passed.")
