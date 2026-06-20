"""Regression harness for TC-001..003 — golden-dataset score ranges (Saba, Step 4).

README_Saba acceptance targets:
  TC-001 authentic image   -> score 0.8-1.0, status compliant
  TC-002 AI-generated image-> score 0.0-0.3, status non-compliant
  TC-003 edited image      -> score 0.3-0.7, status review
  plus suite-level: Scoring Accuracy >= 85%, FPR <= 10%, FNR <= 10%

The scoring pipeline is on devel, but the labelled images come from Youssef's
golden dataset, which isn't in the repo yet. So this file is a *ready* harness:
it discovers the dataset via the SYBOL_GOLDEN_DATASET env var (or the default
qa/test_cases/golden/ path) and a manifest.json, and skips with a clear reason
until that exists. The moment the dataset lands, these tests run with no code
changes — just drop the files in and set the path.

Expected manifest.json shape (list of records):
  [
    {"file": "authentic/img001.jpg", "label": "authentic"},
    {"file": "ai/img045.png",        "label": "ai_generated"},
    {"file": "edited/img080.jpg",     "label": "edited"}
  ]
"""

import json
import os
from pathlib import Path

import pytest

from scoring.models import ComplianceStatus
from scoring.pipeline import score_image

# Per-label expected score band and target status (from README_Saba TC-001..003).
LABEL_EXPECTATIONS = {
    "authentic": ((0.8, 1.0), ComplianceStatus.COMPLIANT),
    "ai_generated": ((0.0, 0.3), ComplianceStatus.NON_COMPLIANT),
    "edited": ((0.3, 0.7), ComplianceStatus.REVIEW),
}

# Suite-level acceptance gates.
MIN_ACCURACY = 0.85
MAX_FALSE_POSITIVE_RATE = 0.10  # AI/edited wrongly scored as authentic-compliant
MAX_FALSE_NEGATIVE_RATE = 0.10  # authentic wrongly scored as non-compliant


def _dataset_dir() -> Path:
    override = os.getenv("SYBOL_GOLDEN_DATASET")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "qa" / "test_cases" / "golden"


def _load_manifest():
    root = _dataset_dir()
    manifest = root / "manifest.json"
    if not manifest.exists():
        pytest.skip(
            f"Golden dataset not found at {root} (no manifest.json). "
            "Set SYBOL_GOLDEN_DATASET or add Youssef's dataset to enable TC-001..003."
        )
    records = json.loads(manifest.read_text())
    cases = []
    for rec in records:
        label = rec["label"]
        if label not in LABEL_EXPECTATIONS:
            pytest.fail(
                f"Unknown label {label!r} in manifest; expected one of {list(LABEL_EXPECTATIONS)}"
            )
        cases.append((root / rec["file"], label))
    if not cases:
        pytest.skip("Golden dataset manifest is empty.")
    return root, cases


@pytest.fixture(autouse=True)
def _ensure_provenance_reference_index():
    """Golden authentic labels assume qa/test_cases/authentic/ is indexed."""
    from scoring.provenance import rebuild_provenance_index

    rebuild_provenance_index()


def _score_one(path: Path):
    content = path.read_bytes()
    return score_image(content, filename=path.name)


def _pytest_id(case):
    path, label = case
    return f"{label}:{path.name}"


def test_dataset_present_and_labelled():
    # Guards the data contract itself: every referenced file actually exists.
    root, cases = _load_manifest()
    missing = [str(p) for p, _ in cases if not p.exists()]
    assert not missing, "Manifest references missing files:\n" + "\n".join(missing)


def test_per_image_score_bands():
    # TC-001..003: each labelled image lands in its expected band and status.
    _root, cases = _load_manifest()
    failures = []
    for path, label in cases:
        (lo, hi), expected_status = LABEL_EXPECTATIONS[label]
        result = _score_one(path)
        if not (lo <= result.authenticity_score <= hi):
            failures.append(
                f"{path.name} [{label}]: score {result.authenticity_score:.3f} "
                f"outside [{lo}, {hi}]"
            )
        elif result.compliance_status != expected_status:
            failures.append(
                f"{path.name} [{label}]: status {result.compliance_status.value} "
                f"!= {expected_status.value}"
            )
    assert not failures, "Per-image band failures:\n" + "\n".join(failures)


def test_suite_level_accuracy_and_error_rates():
    # Aggregate gates: accuracy >= 85%, FPR <= 10%, FNR <= 10%.
    _root, cases = _load_manifest()
    total = len(cases)
    correct = 0
    false_positives = 0  # not-authentic predicted compliant
    false_negatives = 0  # authentic predicted not-compliant
    n_authentic = sum(1 for _, label in cases if label == "authentic")
    n_not_authentic = total - n_authentic

    for path, label in cases:
        _expected_band, expected_status = LABEL_EXPECTATIONS[label]
        status = _score_one(path).compliance_status
        if status == expected_status:
            correct += 1
        if label == "authentic" and status != ComplianceStatus.COMPLIANT:
            false_negatives += 1
        if label != "authentic" and status == ComplianceStatus.COMPLIANT:
            false_positives += 1

    accuracy = correct / total
    fpr = (false_positives / n_not_authentic) if n_not_authentic else 0.0
    fnr = (false_negatives / n_authentic) if n_authentic else 0.0

    assert accuracy >= MIN_ACCURACY, f"accuracy {accuracy:.1%} < {MIN_ACCURACY:.0%}"
    assert (
        fpr <= MAX_FALSE_POSITIVE_RATE
    ), f"FPR {fpr:.1%} > {MAX_FALSE_POSITIVE_RATE:.0%}"
    assert (
        fnr <= MAX_FALSE_NEGATIVE_RATE
    ), f"FNR {fnr:.1%} > {MAX_FALSE_NEGATIVE_RATE:.0%}"
