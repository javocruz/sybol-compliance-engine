#!/usr/bin/env python3
"""Fit Platt scaling parameters from the golden dataset (optional calibration)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
from sklearn.linear_model import LogisticRegression

from scoring.constants import WM, WA, WP, WV
from scoring.pipeline import score_image
from scoring.provenance import rebuild_provenance_index

GOLDEN_DIR = ROOT / "qa" / "test_cases" / "golden"
OUT_PATH = ROOT / "src" / "scoring" / "data" / "platt_params.json"


def _raw_weighted(path: Path) -> float:
    result = score_image(path.read_bytes(), filename=path.name)
    b = result.score_breakdown
    return WM * b.m + WA * b.a + WV * b.v + WP * b.p


def main() -> None:
    rebuild_provenance_index()
    manifest = json.loads((GOLDEN_DIR / "manifest.json").read_text())
    xs: list[float] = []
    ys: list[int] = []
    for rec in manifest:
        path = GOLDEN_DIR / rec["file"]
        xs.append(_raw_weighted(path))
        ys.append(1 if rec["label"] == "authentic" else 0)

    x_arr = np.array(xs).reshape(-1, 1)
    y_arr = np.array(ys)
    model = LogisticRegression(C=1e6, max_iter=1000)
    model.fit(x_arr, y_arr)
    a = float(model.coef_[0][0])
    b = float(model.intercept_[0])

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({"a": a, "b": b}, indent=2) + "\n")
    print(f"Wrote Platt params to {OUT_PATH}")
    print(f"  a={a:.4f}, b={b:.4f}")


if __name__ == "__main__":
    main()
