import hashlib
import io
from dataclasses import dataclass
from typing import Any

import exifread
from PIL import Image, UnidentifiedImageError

from .constants import MODEL_INPUT_SIZE, SUPPORTED_MIME_TYPES


class ScoringError(Exception):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


@dataclass
class PreprocessedImage:
    raw_bytes: bytes
    media_hash: str
    exif_tags: dict[str, Any]
    original_image: Image.Image
    model_image: Image.Image
    content_type: str | None


def _extract_exif_tags(raw_bytes: bytes) -> dict[str, Any]:
    tags: dict[str, Any] = {}
    stream = io.BytesIO(raw_bytes)
    # EXIF is best-effort metadata: a malformed/truncated file can make exifread
    # raise (e.g. UnicodeDecodeError on a corrupt PNG chunk). Treat any parse
    # failure as "no EXIF" so the real corruption is caught later by Image.load()
    # and surfaced as a clean ScoringError rather than a 500.
    try:
        exif = exifread.process_file(stream, details=False)
    except Exception:
        return tags
    for tag_name, value in exif.items():
        if tag_name in ("JPEGThumbnail", "TIFFThumbnail", "Filename", "EXIF MakerNote"):
            continue
        tags[tag_name] = str(value)
    return tags


def _detect_format(raw_bytes: bytes) -> str | None:
    if raw_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if raw_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if raw_bytes[:4] == b"RIFF" and raw_bytes[8:12] == b"WEBP":
        return "image/webp"
    return None


def preprocess(
    raw_bytes: bytes,
    filename: str | None = None,
    content_type: str | None = None,
) -> PreprocessedImage:
    if not raw_bytes:
        raise ScoringError("Empty file", "empty_file")

    detected = _detect_format(raw_bytes)
    if detected is None:
        raise ScoringError(
            "Unsupported or unrecognized image format", "unsupported_format"
        )

    if content_type and content_type not in SUPPORTED_MIME_TYPES:
        raise ScoringError(
            f"Unsupported file type: {content_type}", "unsupported_format"
        )

    media_hash = hashlib.sha256(raw_bytes).hexdigest()
    exif_tags = _extract_exif_tags(raw_bytes)

    try:
        original_image = Image.open(io.BytesIO(raw_bytes))
        original_image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ScoringError("Corrupted or unreadable image", "corrupted_file") from exc

    original_rgb = original_image.convert("RGB")
    model_image = original_rgb.resize(
        (MODEL_INPUT_SIZE, MODEL_INPUT_SIZE), Image.Resampling.LANCZOS
    )

    return PreprocessedImage(
        raw_bytes=raw_bytes,
        media_hash=media_hash,
        exif_tags=exif_tags,
        original_image=original_rgb,
        model_image=model_image,
        content_type=content_type or detected,
    )
