"""TC-005 — RAG retrieval metrics: precision / recall / hallucination (Saba).

README_Saba acceptance targets:
  RAG Precision      >= 80%
  RAG Recall         >= 75%
  Hallucination Rate <= 5%

This is a *ready* harness, mirroring the golden-regression pattern. It runs the
labelled queries in qa/test_cases/rag_eval/queries.json through the real
`query_regulations` against a live index, then scores the returned
regulation_refs against the expected regulations per query.

It needs a populated Qdrant index (the 5 PDFs in research/regulations/ ingested
via `python -m scripts.ingest`) plus a MISTRAL_API_KEY for synthesis. When those
aren't available it skips with a clear reason, and activates automatically once
Engineering brings RAG up — no code change here.

Metric definitions (per query, regulation-level):
  * precision = |returned ∩ expected| / |returned|
  * recall    = |returned ∩ expected| / |expected|
  * hallucination = any returned regulation not in the closed corpus set
Reported figures are macro-averages across the query set.
"""

import json
import os
from pathlib import Path

import pytest

EVAL_PATH = (
    Path(__file__).resolve().parents[2]
    / "qa"
    / "test_cases"
    / "rag_eval"
    / "queries.json"
)

MIN_PRECISION = 0.80
MIN_RECALL = 0.75
MAX_HALLUCINATION = 0.05


def _qdrant_up() -> bool:
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    try:
        import httpx

        return httpx.get(url.rstrip("/") + "/healthz", timeout=1.0).status_code < 400
    except Exception:
        return False


requires_live_rag = pytest.mark.skipif(
    not (_qdrant_up() and os.getenv("MISTRAL_API_KEY")),
    reason="Live RAG not available (needs Qdrant up with PDFs ingested + MISTRAL_API_KEY). "
    "TC-005 metrics skipped until Engineering brings RAG online.",
)


def _load_eval():
    if not EVAL_PATH.exists():
        pytest.skip(f"RAG eval set not found at {EVAL_PATH}")
    return json.loads(EVAL_PATH.read_text())


def _norm(s: str) -> str:
    return s.strip().casefold()


@pytest.fixture(scope="module")
def live_index():
    # Build the index the same way the app does at startup.
    from rag.pipeline import load_index

    index, _ = load_index()
    if index is None:
        pytest.skip("load_index() returned None (index not populated).")
    return index


def _run_query(index, query: str):
    from rag.query import query_regulations

    result = query_regulations(query, index)
    returned = {_norm(r.regulation) for r in result.regulation_refs}
    return returned, result


@requires_live_rag
def test_corpus_has_no_hallucinated_regulations(live_index):
    # Every returned regulation must be one of the known corpus documents.
    data = _load_eval()
    corpus = {_norm(r) for r in data["corpus_regulations"]}
    offenders = []
    for q in data["queries"]:
        returned, _ = _run_query(live_index, q["query"])
        for reg in returned - corpus:
            offenders.append(f"{q['id']}: hallucinated regulation {reg!r}")
    rate = len(offenders) / max(1, sum(1 for _ in data["queries"]))
    assert (
        rate <= MAX_HALLUCINATION
    ), f"Hallucination rate {rate:.0%} > {MAX_HALLUCINATION:.0%}:\n" + "\n".join(
        offenders
    )


@requires_live_rag
def test_rag_precision_and_recall_meet_targets(live_index):
    data = _load_eval()
    precisions, recalls = [], []
    detail = []
    for q in data["queries"]:
        expected = {_norm(r) for r in q["expected_regulations"]}
        returned, _ = _run_query(live_index, q["query"])
        hits = returned & expected
        precision = len(hits) / len(returned) if returned else 0.0
        recall = len(hits) / len(expected) if expected else 1.0
        precisions.append(precision)
        recalls.append(recall)
        detail.append(
            f"{q['id']}: P={precision:.2f} R={recall:.2f} "
            f"(expected={sorted(expected)}, got={sorted(returned)})"
        )

    macro_p = sum(precisions) / len(precisions)
    macro_r = sum(recalls) / len(recalls)
    report = "\n".join(detail)
    assert (
        macro_p >= MIN_PRECISION
    ), f"precision {macro_p:.0%} < {MIN_PRECISION:.0%}\n{report}"
    assert macro_r >= MIN_RECALL, f"recall {macro_r:.0%} < {MIN_RECALL:.0%}\n{report}"


@requires_live_rag
def test_every_query_returns_at_least_one_ref(live_index):
    # A no-result answer on an in-corpus query is a retrieval failure.
    data = _load_eval()
    empty = []
    for q in data["queries"]:
        returned, result = _run_query(live_index, q["query"])
        if not result.regulation_refs:
            empty.append(q["id"])
    assert not empty, f"queries returned zero regulation_refs: {empty}"
