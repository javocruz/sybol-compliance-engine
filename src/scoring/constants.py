from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Signal weights (sum to 1.0) — calibrated on golden dataset, Jun 2026.
WM = 0.18
WA = 0.22
WV = 0.15
WP = 0.45

THRESHOLD_NON_COMPLIANT = 0.3
THRESHOLD_COMPLIANT = 0.7

# Post-weight rules in scorer.py (see compute_authenticity_score).
PROVENANCE_MATCH_MIN = 0.90
PROVENANCE_MATCH_SCORE_FLOOR = 0.82
EXIF_RICH_METADATA_MIN = 0.72
EXIF_RICH_SCORE_FLOOR = 0.80
SYNTHETIC_PROFILE_PROVENANCE_MAX = 0.28
SYNTHETIC_PROFILE_METADATA_MAX = 0.45
SYNTHETIC_PROFILE_SCORE_CAP = 0.26
# PNG/WebP often ship without EXIF — neutral metadata band, not treated as stripped JPEG.
PNG_NEUTRAL_METADATA_MIN = 0.44
PNG_NEUTRAL_METADATA_MAX = 0.52
# Escape synthetic cap when artifact + visual signals look camera-captured.
CAMERA_LIKELY_ARTIFACT_MIN = 0.76
CAMERA_LIKELY_VISUAL_MIN = 0.72
EDITED_PROFILE_METADATA_MIN = 0.45
EDITED_PROFILE_METADATA_MAX = 0.72
EDITED_PROFILE_ARTIFACT_MIN = 0.38
EDITED_PROFILE_ARTIFACT_MAX = 0.78
EDITED_PROFILE_PROVENANCE_MAX = 0.55
EDITED_PROFILE_SCORE_MIN = 0.35
EDITED_PROFILE_SCORE_MAX = 0.65

DEEPFAKE_MODEL_ID = "dima806/deepfake_vs_real_image_detection"
MODEL_INPUT_SIZE = 224

EDITING_SOFTWARE_TAGS = (
    "photoshop",
    "gimp",
    "stable diffusion",
    "midjourney",
    "dall-e",
    "dalle",
    "adobe",
    "lightroom",
    "canva",
    "affinity",
)

REQUIRED_EXIF_FIELDS = ("DateTimeOriginal", "Make", "Model")

# Sub-score weights inside signal extractors
ARTIFACT_CNN_WEIGHT = 0.50
ARTIFACT_FFT_WEIGHT = 0.25
ARTIFACT_NOISE_WEIGHT = 0.25
ARTIFACT_SYNTHETIC_FAKE_WEIGHT = 0.62
ARTIFACT_SYNTHETIC_FFT_WEIGHT = 0.25
ARTIFACT_SYNTHETIC_NOISE_WEIGHT = 0.20

METADATA_PRESENCE_WEIGHT = 0.35
METADATA_FIELDS_WEIGHT = 0.35
METADATA_SOFTWARE_WEIGHT = 0.20
METADATA_TIMESTAMP_WEIGHT = 0.10

NO_EXIF_CAP = 0.35
# Missing EXIF on PNG/WebP is normal — not evidence of synthesis (unlike stripped JPEG).
PNG_WEBP_NO_EXIF_SCORE = 0.55

PHASH_MATCH_THRESHOLD = 10
AUTHENTIC_REFERENCE_DIR = PROJECT_ROOT / "qa" / "test_cases" / "authentic"
EMPTY_PROVENANCE_DEFAULT = 0.5

PLATT_ENABLED = False
PLATT_PARAMS_PATH = Path(__file__).resolve().parent / "data" / "platt_params.json"

SUPPORTED_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
