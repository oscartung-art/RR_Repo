from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _ingest_test_utils import build_enriched_row


def test_subject_normalization_keeps_only_the_leaf_before_prefixing():
    cases = [
        ("Sculpture", "Object/Sculpture"),
        ("Object/Sculpture", "Object/Sculpture"),
        ("Object/Decor/Sculpture", "Object/Sculpture"),
        ("modern_sculpture", "Object/Modern Sculpture"),
        ("Modern-Sculpture", "Object/Modern Sculpture"),
    ]

    for ai_subject, expected_subject in cases:
        _, row = build_enriched_row("object", "object_0", {"subject": ai_subject})
        assert row["custom_property_0"] == expected_subject


def test_unknown_subject_stays_unset():
    _, row = build_enriched_row("object", "object_0", {"subject": "-"})
    assert row["custom_property_0"] == "-"


if __name__ == "__main__":
    test_subject_normalization_keeps_only_the_leaf_before_prefixing()
    test_unknown_subject_stays_unset()
    print("All tests passed.")
