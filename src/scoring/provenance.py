from pathlib import Path

import imagehash
from PIL import Image

from .constants import (
    AUTHENTIC_REFERENCE_DIR,
    EMPTY_PROVENANCE_DEFAULT,
    PHASH_MATCH_THRESHOLD,
)
from .preprocess import PreprocessedImage

_provenance_index: dict[str, str] = {}


def _image_extensions() -> tuple[str, ...]:
    return (".jpg", ".jpeg", ".png", ".webp")


def rebuild_provenance_index(reference_dir: Path | None = None) -> dict[str, str]:
    global _provenance_index
    directory = reference_dir or AUTHENTIC_REFERENCE_DIR
    index: dict[str, str] = {}

    if directory.exists():
        for path in sorted(directory.iterdir()):
            if path.suffix.lower() not in _image_extensions():
                continue
            try:
                with Image.open(path) as img:
                    phash = str(imagehash.phash(img.convert("RGB")))
                index[phash] = path.name
            except OSError:
                continue

    _provenance_index = index
    return index


def get_provenance_index() -> dict[str, str]:
    if not _provenance_index:
        rebuild_provenance_index()
    return _provenance_index


def _hamming_distance(hash_a: str, hash_b: str) -> int:
    return imagehash.hex_to_hash(hash_a) - imagehash.hex_to_hash(hash_b)


def score_provenance(preprocessed: PreprocessedImage) -> float:
    index = get_provenance_index()
    if not index:
        return EMPTY_PROVENANCE_DEFAULT

    query_hash = str(imagehash.phash(preprocessed.original_image))
    distances = [_hamming_distance(query_hash, ref_hash) for ref_hash in index]
    min_distance = min(distances)

    if min_distance <= PHASH_MATCH_THRESHOLD:
        return max(0.0, min(1.0, 1.0 - min_distance / (PHASH_MATCH_THRESHOLD + 1)))
    return max(0.0, min(1.0, 0.42 - min_distance / 48.0))
