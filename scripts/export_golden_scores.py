#!/usr/bin/env python3
"""Export per-image scoring results for the golden dataset (Saba / tuning review)."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scoring.models import ComplianceStatus  # noqa: E402
from scoring.pipeline import score_image  # noqa: E402

GOLDEN_DIR = ROOT / "qa" / "test_cases" / "golden"
DEFAULT_OUT = GOLDEN_DIR / "scoring_report.csv"

LABEL_EXPECTATIONS = {
    "authentic": ((0.8, 1.0), ComplianceStatus.COMPLIANT),
    "ai_generated": ((0.0, 0.3), ComplianceStatus.NON_COMPLIANT),
    "edited": ((0.3, 0.7), ComplianceStatus.REVIEW),
}


def main() -> None:
    manifest_path = GOLDEN_DIR / "manifest.json"
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT

    records = json.loads(manifest_path.read_text())
    rows: list[dict[str, str | float | bool]] = []

    for rec in records:
        path = GOLDEN_DIR / rec["file"]
        label = rec["label"]
        (lo, hi), expected_status = LABEL_EXPECTATIONS[label]
        result = score_image(path.read_bytes(), filename=path.name)
        band_ok = lo <= result.authenticity_score <= hi
        status_ok = result.compliance_status == expected_status
        b = result.score_breakdown
        rows.append(
            {
                "file": rec["file"],
                "label": label,
                "score": round(result.authenticity_score, 4),
                "status": result.compliance_status.value,
                "expected_status": expected_status.value,
                "band_min": lo,
                "band_max": hi,
                "band_ok": band_ok,
                "status_ok": status_ok,
                "tc_pass": band_ok and status_ok,
                "metadata_m": round(b.m, 4),
                "artifact_a": round(b.a, 4),
                "visual_v": round(b.v, 4),
                "provenance_p": round(b.p, 4),
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with out_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    passed = sum(1 for r in rows if r["tc_pass"])
    print(f"Wrote {len(rows)} rows to {out_path}")
    print(f"TC pass (band + status): {passed}/{len(rows)}")


if __name__ == "__main__":
    main()
