from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from eval.bench import load_bench


def test_load_bench_returns_rows() -> None:
    rows = load_bench()
    assert len(rows) >= 100
    assert "question" in rows[0]
    assert "language" in rows[0]
    assert "ground_truth_citations" in rows[0]


def test_load_bench_respects_sample() -> None:
    rows = load_bench(sample=1)
    assert len(rows) == 1


def test_load_bench_language_filter() -> None:
    en_rows = load_bench(language="en")
    assert len(en_rows) == 10
    assert all(r["language"] == "en" for r in en_rows)

    fr_rows = load_bench(language="fr")
    assert len(fr_rows) == 10

    ar_rows = load_bench(language="ar")
    assert len(ar_rows) == 10


@pytest.mark.asyncio
async def test_eval_runs_without_crash() -> None:
    from api.models import AgentStateUpdate, StateName
    from eval.run_eval import _run_eval

    answer_update = AgentStateUpdate(
        session_id="eval-test",
        state=StateName.ANSWER,
        step_index=4,
        content="Mocked answer text.",
        is_final=True,
        metadata={
            "citations": [],
            "metrics": {
                "faithfulness": None,
                "citation_accuracy": None,
                "latency_seconds": 1.0,
                "cost_usd": 0.0,
                "tokens_in": 0,
                "tokens_out": 0,
                "citation_count": 0,
                "num_search_hops": 0,
            },
        },
    )

    async def _mock_run(_session_id, _query, _language="en"):
        yield answer_update

    mock_agent = MagicMock()
    mock_agent.run = _mock_run

    results = await _run_eval(sample=3, agent=mock_agent)
    assert len(results) == 3
    for r in results:
        assert "faithfulness" in r
        assert "citation_accuracy" in r
        assert "latency_seconds" in r
        assert "language" in r
