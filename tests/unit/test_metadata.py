from scoring.metadata import score_metadata
from scoring.preprocess import PreprocessedImage


def _preprocessed(exif_tags, content_type="image/jpeg"):
    from PIL import Image

    image = Image.new("RGB", (64, 64), color=(10, 20, 30))
    return PreprocessedImage(
        raw_bytes=b"bytes",
        media_hash="abc",
        exif_tags=exif_tags,
        original_image=image,
        model_image=image.resize((224, 224)),
        content_type=content_type,
    )


def test_metadata_high_score_with_complete_exif():
    tags = {
        "Image Make": "Canon",
        "Image Model": "EOS",
        "EXIF DateTimeOriginal": "2024:01:01 12:00:00",
        "EXIF DateTime": "2024:01:01 12:00:00",
        "EXIF DateTimeDigitized": "2024:01:01 12:00:00",
    }
    score = score_metadata(_preprocessed(tags))
    assert 0.7 <= score <= 1.0


def test_metadata_penalizes_ai_software_tag():
    tags = {
        "Image Software": "Stable Diffusion webui",
        "EXIF DateTimeOriginal": "2024:01:01 12:00:00",
    }
    score = score_metadata(_preprocessed(tags))
    assert score < 0.5


def test_metadata_png_without_exif_gets_neutral_score():
    score = score_metadata(_preprocessed({}, content_type="image/png"))
    assert 0.40 <= score <= 0.52


def test_metadata_future_timestamp_penalized():
    tags = {
        "EXIF DateTimeOriginal": "2099:01:01 12:00:00",
        "Image Make": "Canon",
        "Image Model": "EOS",
    }
    score = score_metadata(_preprocessed(tags))
    assert score < 0.7
