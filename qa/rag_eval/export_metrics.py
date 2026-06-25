#!/usr/bin/env python3
"""Export RAG eval metrics to qa/rag_eval/results.json."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

EVAL_PATH = ROOT / "qa" / "test_cases" / "rag_eval" / "queries.json"
OUT_PATH = ROOT / "qa" / "rag_eval" / "results.json"

MIN_PRECISION = 0.80
MIN_RECALL = 0.75
MAX_HALLUCINATION = 0.05


def _norm(s: str) -> str:
    return s.strip().casefold()


def main() -> int:
    if not os.getenv("MISTRAL_API_KEY"):
        print("MISTRAL_API_KEY required for export", file=sys.stderr)
        return 1
    data = json.loads(EVAL_PATH.read_text())
    from rag.pipeline import load_index
    from rag.query import query_regulations

    index, _ = load_index()
    if index is None:
        print("Index not available", file=sys.stderr)
        return 1

    corpus = {_norm(r) for r in data["corpus_regulations"]}
    rows = []
    precisions, recalls = [], []
    hallucination_offenders = []

    for q in data["queries"]:
        time.sleep(1.0)
        result = query_regulations(q["query"], index)
        returned = {_norm(r.regulation) for r in result.regulation_refs}
        expected = {_norm(r) for r in q["expected_regulations"]}
        hits = returned & expected
        precision = len(hits) / len(returned) if returned else 0.0
        recall = len(hits) / len(expected) if expected else 1.0
        precisions.append(precision)
        recalls.append(recall)
        for reg in returned - corpus:
            hallucination_offenders.append(f"{q['id']}: {reg}")
        rows.append(
            {
                "id": q["id"],
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "returned": sorted(returned),
                "expected": sorted(expected),
            }
        )

    macro_p = sum(precisions) / len(precisions)
    macro_r = sum(recalls) / len(recalls)
    hallucination_rate = len(hallucination_offenders) / max(1, len(data["queries"]))

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "macro_precision": round(macro_p, 4),
        "macro_recall": round(macro_r, 4),
        "hallucination_rate": round(hallucination_rate, 4),
        "targets": {
            "min_precision": MIN_PRECISION,
            "min_recall": MIN_RECALL,
            "max_hallucination": MAX_HALLUCINATION,
        },
        "passed": macro_p >= MIN_PRECISION
        and macro_r >= MIN_RECALL
        and hallucination_rate <= MAX_HALLUCINATION,
        "queries": rows,
        "hallucination_offenders": hallucination_offenders,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Wrote {OUT_PATH}")
    return 0 if payload["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
