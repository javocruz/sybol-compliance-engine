from scoring import provenance
from scoring.preprocess import preprocess


def test_empty_index_returns_default(sample_png_bytes, mocker):
    mocker.patch.object(provenance, "get_provenance_index", return_value={})
    preprocessed = preprocess(sample_png_bytes, content_type="image/png")
    score = provenance.score_provenance(preprocessed)
    assert score == 0.5


def test_matching_reference_scores_high(
    sample_png_bytes, authentic_reference_dir, mocker
):
    provenance.rebuild_provenance_index(authentic_reference_dir)
    preprocessed = preprocess(sample_png_bytes, content_type="image/png")
    score = provenance.score_provenance(preprocessed)
    assert 0.0 <= score <= 1.0
    provenance.rebuild_provenance_index()
