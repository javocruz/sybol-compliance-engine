from scoring.artifacts import score_artifacts
from scoring.preprocess import preprocess


def test_score_artifacts_returns_bounded_value(sample_png_bytes, mock_deepfake_model):
    preprocessed = preprocess(sample_png_bytes, content_type="image/png")
    score = score_artifacts(preprocessed)
    assert 0.0 <= score <= 1.0


def test_synthetic_format_uses_fake_probability(sample_png_bytes, mocker):
    preprocessed = preprocess(sample_png_bytes, content_type="image/png")
    mocker.patch("scoring.artifacts.predict_fake_probability", return_value=0.8)
    mocker.patch("scoring.artifacts._fft_score", return_value=0.5)
    mocker.patch("scoring.artifacts._noise_residual_score", return_value=0.5)
    score = score_artifacts(preprocessed)
    assert 0.65 <= score <= 0.75


def test_jpeg_path_uses_authenticity_score(sample_jpeg_bytes, mocker):
    preprocessed = preprocess(sample_jpeg_bytes, content_type="image/jpeg")
    mocker.patch("scoring.artifacts.predict_authenticity_score", return_value=0.9)
    mocker.patch("scoring.artifacts._fft_score", return_value=0.7)
    mocker.patch("scoring.artifacts._noise_residual_score", return_value=0.7)
    score = score_artifacts(preprocessed)
    assert score >= 0.7
