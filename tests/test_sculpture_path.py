from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _ingest_test_utils import build_enriched_row


def test_filename_prefix_codes_do_not_override_ai_subject():
    _, row = build_enriched_row(
        "object",
        "12-11 object_0",
        {
            "subject": "Sculpture",
            "model_name": "-",
            "brand": "-",
            "collection": "-",
            "primary_material_or_color": "-",
            "usage_location": "-",
            "shape_form": "-",
            "period": "-",
            "size": "-",
            "vendor_name": "-",
        },
    )

    assert row["Subject"] == "Object/Sculpture"


if __name__ == "__main__":
    test_filename_prefix_codes_do_not_override_ai_subject()
    print("All tests passed.")
