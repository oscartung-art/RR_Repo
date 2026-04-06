import numpy as np
import pandas as pd

from scripts import image_vibe


def make_index():
    return pd.DataFrame(
        {
            "path": ["alpha.png", "beta.png", "gamma.png"],
            "vector": [
                np.array([10.0, 0.0], dtype=np.float32),
                np.array([0.0, 5.0], dtype=np.float32),
                np.array([1.0, 1.0], dtype=np.float32),
            ],
        }
    )


def test_find_matches_returns_descending_cosine_similarity():
    matches = image_vibe.find_matches(np.array([1.0, 0.0]), make_index(), top_k=2)

    assert matches["path"].tolist() == ["alpha.png", "gamma.png"]
    assert matches["score"].iloc[0] > matches["score"].iloc[1]


def test_find_matches_deduplicates_duplicate_paths():
    index_df = pd.DataFrame(
        {
            "path": ["alpha.png", "alpha.png", "beta.png"],
            "vector": [
                np.array([10.0, 0.0], dtype=np.float32),
                np.array([9.0, 0.0], dtype=np.float32),
                np.array([0.0, 5.0], dtype=np.float32),
            ],
        }
    )

    matches = image_vibe.find_matches(np.array([1.0, 0.0]), index_df, top_k=3)

    assert matches["path"].tolist() == ["alpha.png", "beta.png"]


def test_format_everything_or_quotes_and_escapes_terms():
    search = image_vibe.format_everything_or([r"G:\Asset One.png", 'odd"name.png'])

    assert search == '"G:\\Asset One.png"|"odd""name.png"'


def test_build_vector_matrix_rejects_mixed_dimensions():
    index_df = pd.DataFrame(
        {
            "path": ["one.png", "two.png"],
            "vector": [np.array([1.0, 0.0]), np.array([1.0, 0.0, 0.0])],
        }
    )

    try:
        image_vibe.build_vector_matrix(index_df, "vector")
    except ValueError as exc:
        assert "same dimension" in str(exc)
    else:
        raise AssertionError("Expected mixed dimensions to fail.")


def test_load_image_from_path_requires_existing_file(tmp_path):
    missing = tmp_path / "missing.png"

    try:
        image_vibe.load_image_from_path(missing)
    except FileNotFoundError as exc:
        assert str(missing) in str(exc)
    else:
        raise AssertionError("Expected a missing image path to fail.")


def test_reverse_image_search_uses_injected_writer(monkeypatch):
    written = {}

    monkeypatch.setattr(
        image_vibe,
        "encode_image",
        lambda image, model, preprocess, device: np.array([1.0, 0.0], dtype=np.float32),
    )

    config = image_vibe.SearchConfig(top_k=2)
    search_string, matches = image_vibe.reverse_image_search(
        config=config,
        image=object(),
        index_df=make_index(),
        model_bundle=(object(), object(), "cpu"),
        clipboard_writer=lambda text: written.setdefault("text", text),
    )

    assert search_string == '"alpha.png"|"gamma.png"'
    assert written["text"] == search_string
    assert matches["path"].tolist() == ["alpha.png", "gamma.png"]


def test_parse_args_accepts_image_path():
    args = image_vibe.parse_args(["--image-path", "sample.png", "--dry-run"])

    assert args.image_path == "sample.png"
    assert args.dry_run is True