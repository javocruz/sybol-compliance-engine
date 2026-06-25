from datetime import datetime
from typing import Any

from .constants import (
    EDITING_SOFTWARE_TAGS,
    METADATA_FIELDS_WEIGHT,
    METADATA_PRESENCE_WEIGHT,
    METADATA_SOFTWARE_WEIGHT,
    METADATA_TIMESTAMP_WEIGHT,
    NO_EXIF_CAP,
    PNG_WEBP_NO_EXIF_SCORE,
    REQUIRED_EXIF_FIELDS,
)
from .preprocess import PreprocessedImage


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _exif_value(tags: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        if key in tags:
            return str(tags[key])
        for tag_key, value in tags.items():
            if tag_key.endswith(key):
                return str(value)
    return None


def _presence_score(tags: dict[str, Any], content_type: str | None) -> float:
    if tags:
        return 1.0
    if content_type in ("image/png", "image/webp"):
        return PNG_WEBP_NO_EXIF_SCORE
    return NO_EXIF_CAP


def _required_fields_score(tags: dict[str, Any]) -> float:
    if not tags:
        return 0.0
    present = sum(1 for field in REQUIRED_EXIF_FIELDS if _exif_value(tags, field))
    base = present / len(REQUIRED_EXIF_FIELDS)
    make = _exif_value(tags, "Make")
    model = _exif_value(tags, "Model")
    if make and model and present >= 2:
        return _clamp(base + 0.15)
    return base


def _software_score(tags: dict[str, Any]) -> float:
    software = _exif_value(tags, "Software", "ProcessingSoftware")
    if not software:
        return 1.0
    software_lower = software.lower()
    for tag in EDITING_SOFTWARE_TAGS:
        if tag in software_lower:
            if tag in ("stable diffusion", "midjourney", "dall-e", "dalle"):
                return 0.0
            return 0.2
    return 1.0


def _parse_exif_datetime(value: str) -> datetime | None:
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _timestamp_score(tags: dict[str, Any]) -> float:
    timestamps: list[datetime] = []
    for key in ("DateTime", "DateTimeOriginal", "DateTimeDigitized"):
        raw = _exif_value(tags, f"EXIF {key}", f"Image {key}", key)
        if raw:
            parsed = _parse_exif_datetime(raw)
            if parsed:
                timestamps.append(parsed)

    if not timestamps:
        return 0.7

    now = datetime.now()
    if any(ts > now for ts in timestamps):
        return 0.1

    if len(timestamps) >= 2:
        deltas = [
            abs((timestamps[i] - timestamps[j]).total_seconds())
            for i in range(len(timestamps))
            for j in range(i + 1, len(timestamps))
        ]
        if deltas and max(deltas) > 86400:
            return 0.4

    return 1.0


def score_metadata(preprocessed: PreprocessedImage) -> float:
    tags = preprocessed.exif_tags
    presence = _presence_score(tags, preprocessed.content_type)
    fields = _required_fields_score(tags)
    software = _software_score(tags)
    timestamp = _timestamp_score(tags)

    score = (
        METADATA_PRESENCE_WEIGHT * presence
        + METADATA_FIELDS_WEIGHT * fields
        + METADATA_SOFTWARE_WEIGHT * software
        + METADATA_TIMESTAMP_WEIGHT * timestamp
    )

    if software <= 0.2:
        score = min(score, 0.35)
    if timestamp <= 0.2:
        score = min(score, 0.45)

    return _clamp(score)
