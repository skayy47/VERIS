from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from utils.helpers import get_logger

logger = get_logger(__name__)

_JUDGE_MODEL = "claude-haiku-4-5-20251001"


class EvalMetrics(BaseModel):
    faithfulness: float
    citation_accuracy: float
    latency_seconds: float
    cost_usd: float
    tokens_in: int
    tokens_out: int
    citation_count: int
    num_search_hops: int


async def _judge_faithfulness(answer: str, snippets: list[str], api_key: str) -> float:
    """LLM-as-judge: score answer faithfulness against retrieved snippets (0.0–1.0)."""
    if not snippets or not answer.strip():
        return 0.0
    import anthropic

    evidence_block = "\n".join(f"[{i + 1}] {s[:200]}" for i, s in enumerate(snippets[:10]))
    prompt = (
        "You are a faithfulness judge. Rate how well the answer is grounded in the provided evidence.\n\n"
        f"Answer:\n{answer[:1000]}\n\n"
        f"Evidence snippets:\n{evidence_block}\n\n"
        "Reply with ONLY a decimal number between 0.0 (not grounded) and 1.0 (fully grounded). "
        "No other text."
    )
    client = anthropic.AsyncAnthropic(api_key=api_key)
    try:
        response = await client.messages.create(
            model=_JUDGE_MODEL,
            max_tokens=8,
            messages=[{"role": "user", "content": prompt}],
        )
        score_text = response.content[0].text.strip()
        return max(0.0, min(1.0, float(score_text)))
    except Exception as exc:
        logger.warning("Faithfulness judge failed: %s", exc)
        return 0.0


def citation_accuracy(predicted_urls: list[str], ground_truth_urls: list[str]) -> float:
    if not ground_truth_urls:
        return 1.0
    matched = sum(
        1 for gt in ground_truth_urls if any(gt in pred or pred in gt for pred in predicted_urls)
    )
    return round(matched / len(ground_truth_urls), 4)


async def compute_all(
    answer: str,
    citations: list[dict[str, Any]],
    ground_truth_citations: list[str],
    latency_seconds: float,
    cost_usd: float,
    tokens_in: int,
    tokens_out: int,
    citation_count: int,
    num_search_hops: int,
    api_key: str = "",
) -> EvalMetrics:
    snippets = [c.get("snippet", "") for c in citations]
    predicted_urls = [c.get("url", "") for c in citations]

    faithfulness = (
        await _judge_faithfulness(answer, snippets, api_key) if api_key else 0.0
    )
    cit_acc = citation_accuracy(predicted_urls, ground_truth_citations)

    return EvalMetrics(
        faithfulness=faithfulness,
        citation_accuracy=cit_acc,
        latency_seconds=round(latency_seconds, 2),
        cost_usd=round(cost_usd, 6),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        citation_count=citation_count,
        num_search_hops=num_search_hops,
    )
