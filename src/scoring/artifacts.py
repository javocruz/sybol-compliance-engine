from typing import cast

import cv2
import numpy as np

from .constants import (
    ARTIFACT_CNN_WEIGHT,
    ARTIFACT_FFT_WEIGHT,
    ARTIFACT_NOISE_WEIGHT,
    ARTIFACT_SYNTHETIC_FAKE_WEIGHT,
    ARTIFACT_SYNTHETIC_FFT_WEIGHT,
    ARTIFACT_SYNTHETIC_NOISE_WEIGHT,
)
from .detector import predict_authenticity_score, predict_fake_probability
from .preprocess import PreprocessedImage


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _is_synthetic_format(preprocessed: PreprocessedImage) -> bool:
    return preprocessed.content_type in ("image/png", "image/webp") and not preprocessed.exif_tags


def _fft_score(model_image) -> float:
    gray = np.asarray(model_image.convert("L"), dtype=np.float32)
    if gray.size == 0:
        return 0.5

    spectrum = np.fft.fftshift(np.fft.fft2(gray))
    magnitude = np.log1p(np.abs(spectrum))

    h, w = magnitude.shape
    cy, cx = h // 2, w // 2
    y, x = np.ogrid[:h, :w]
    radius = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    max_radius = radius.max() or 1.0

    low_mask = radius <= max_radius * 0.2
    high_mask = radius >= max_radius * 0.6

    low_energy = float(magnitude[low_mask].mean()) if low_mask.any() else 0.0
    high_energy = float(magnitude[high_mask].mean()) if high_mask.any() else 0.0
    ratio = high_energy / (low_energy + 1e-6)

    # Natural images: moderate high/low ratio. Grid-like GAN artifacts spike high bands.
    if ratio > 1.8:
        return _clamp(1.0 - (ratio - 1.8) / 2.0)
    return _clamp(0.6 + (1.8 - ratio) * 0.2)


def _noise_residual_score(model_image) -> float:
    gray = np.asarray(model_image.convert("L"), dtype=np.float32)
    if gray.size == 0:
        return 0.5

    blurred = cv2.GaussianBlur(cast(np.ndarray, gray), (0, 0), 1.5)
    residual = gray - blurred
    variance = float(np.var(cast(np.ndarray, residual)))

    # Very low residual variance suggests overly smooth synthetic imagery.
    if variance < 5.0:
        return _clamp(variance / 5.0)
    if variance > 200.0:
        return 0.7
    return _clamp(0.5 + min(variance, 100.0) / 200.0)


def score_artifacts(preprocessed: PreprocessedImage) -> float:
    fft_score = _fft_score(preprocessed.model_image)
    noise_score = _noise_residual_score(preprocessed.model_image)

    if _is_synthetic_format(preprocessed):
        # PNG/WebP without EXIF: lean on fake probability — CNN "real" scores mislead here.
        fake_prob = predict_fake_probability(preprocessed.model_image)
        return _clamp(
            ARTIFACT_SYNTHETIC_FAKE_WEIGHT * fake_prob
            + ARTIFACT_SYNTHETIC_FFT_WEIGHT * fft_score
            + ARTIFACT_SYNTHETIC_NOISE_WEIGHT * noise_score
        )

    cnn_score = predict_authenticity_score(preprocessed.model_image)
    combined = (
        ARTIFACT_CNN_WEIGHT * cnn_score
        + ARTIFACT_FFT_WEIGHT * fft_score
        + ARTIFACT_NOISE_WEIGHT * noise_score
    )
    return _clamp(combined)
