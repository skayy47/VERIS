from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from eval.bench import load_bench
from eval.metrics import EvalMetrics, compute_all
from utils.helpers import get_logger

logger = get_logger(__name__)

_OUTPUT_DIR = Path(__file__).parent / "output"
_LATEST_PATH = _OUTPUT_DIR / "latest.json"


def _build_agent():
    from orchestrator.agent import AsyncAgent
    from orchestrator.router import ModelRouter
    from orchestrator.tools.citations import CitationExtractorTool
    from orchestrator.tools.search import TavilySearchTool
    from utils.config import get_settings

    settings = get_settings()
    return AsyncAgent(
        settings=settings,
        model_router=ModelRouter(settings),
        search_tool=TavilySearchTool(api_key=settings.tavily_api_key),
        citation_tool=CitationExtractorTool(),
        episodic=None,
    )


def _print_table(results: list[dict[str, Any]]) -> None:
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="VERIS Eval Results")
        table.add_column("ID", style="cyan")
        table.add_column("Lang")
        table.add_column("Faithful", justify="right")
        table.add_column("CitAcc", justify="right")
        table.add_column("Latency(s)", justify="right")
        table.add_column("Cost($)", justify="right")
        for r in results:
            table.add_row(
                r["id"],
                r["language"],
                f"{r['faithfulness']:.3f}",
                f"{r['citation_accuracy']:.3f}",
                f"{r['latency_seconds']:.2f}",
                f"{r['cost_usd']:.5f}",
            )
        console.print(table)
    except ImportError:
        for r in results:
            print(r)


def _aggregate_metrics(results: list[dict[str, Any]]) -> EvalMetrics:
    """Average per-query results into a single EvalMetrics for MLflow logging."""
    n = len(results)
    if n == 0:
        return EvalMetrics(
            faithfulness=0.0,
            citation_accuracy=0.0,
            latency_seconds=0.0,
            cost_usd=0.0,
            tokens_in=0,
            tokens_out=0,
            citation_count=0,
            num_search_hops=0,
        )
    return EvalMetrics(
        faithfulness=sum(r["faithfulness"] for r in results) / n,
        citation_accuracy=sum(r["citation_accuracy"] for r in results) / n,
        latency_seconds=sum(r["latency_seconds"] for r in results) / n,
        cost_usd=sum(r["cost_usd"] for r in results),
        tokens_in=sum(r["tokens_in"] for r in results),
        tokens_out=sum(r["tokens_out"] for r in results),
        citation_count=int(sum(r["citation_count"] for r in results) / n),
        num_search_hops=int(sum(r["num_search_hops"] for r in results) / n),
    )


async def _run_eval(
    sample: int,
    language: str | None = None,
    agent: Any = None,
) -> list[dict[str, Any]]:
    rows = load_bench(sample=sample, language=language)

    _agent = agent
    api_key = ""
    if _agent is None:
        from utils.config import get_settings

        settings = get_settings()
        api_key = settings.anthropic_api_key
        _agent = _build_agent()

    results: list[dict[str, Any]] = []
    for row in rows:
        session_id = f"eval-{row['id']}"
        query: str = row["question"]
        lang: str = row["language"]
        t0 = time.monotonic()
        answer = ""
        citations: list[dict[str, Any]] = []
        metrics_meta: dict[str, Any] = {}

        try:
            async for update in _agent.run(session_id, query, lang):
                if update.state == "answer":
                    answer = update.content
                    citations = update.metadata.get("citations", [])
                    metrics_meta = update.metadata.get("metrics", {})
        except Exception as exc:
            logger.error("Agent failed for %s: %s", row["id"], exc)

        latency = time.monotonic() - t0
        eval_metrics = await compute_all(
            answer=answer,
            citations=citations,
            ground_truth_citations=row.get("ground_truth_citations", []),
            latency_seconds=latency,
            cost_usd=metrics_meta.get("cost_usd", 0.0),
            tokens_in=int(metrics_meta.get("tokens_in", 0)),
            tokens_out=int(metrics_meta.get("tokens_out", 0)),
            citation_count=int(metrics_meta.get("citation_count", 0)),
            num_search_hops=int(metrics_meta.get("num_search_hops", 0)),
            api_key=api_key,
        )
        result = {"id": row["id"], "language": lang, **eval_metrics.model_dump()}
        results.append(result)
        logger.info("Evaluated %s: faithfulness=%.3f", row["id"], eval_metrics.faithfulness)

    return results


def _update_eval_gauges(results: list[dict[str, Any]]) -> None:
    """Push per-language faithfulness + citation_accuracy to Prometheus Gauges."""
    try:
        from ops.otel import update_eval_gauges

        per_lang: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        for r in results:
            per_lang[r["language"]]["faithfulness"].append(r["faithfulness"])
            per_lang[r["language"]]["citation_accuracy"].append(r["citation_accuracy"])

        update_eval_gauges(
            {
                lang: {
                    k: sum(vals) / len(vals) for k, vals in metrics.items()
                }
                for lang, metrics in per_lang.items()
            }
        )
    except Exception as exc:
        logger.warning("Failed to update Prometheus eval gauges: %s", exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="VERIS eval harness")
    parser.add_argument("--sample", type=int, default=3)
    parser.add_argument("--language", type=str, default=None, help="Filter by language code")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    parser.add_argument("--output", type=str, default=None, help="Write JSON to path")
    args = parser.parse_args()

    results = asyncio.run(_run_eval(args.sample, language=args.language))
    _print_table(results)

    if args.json:
        print(json.dumps(results, indent=2))

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _LATEST_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    logger.info("Results written to %s", _LATEST_PATH)

    if args.output:
        Path(args.output).write_text(json.dumps(results, indent=2), encoding="utf-8")

    _update_eval_gauges(results)

    # Log to MLflow (skip in test mode or if tracking URI not set)
    if results:
        try:
            from utils.config import get_settings

            settings = get_settings()
            if not settings.testing and settings.mlflow_tracking_uri:
                from ops.mlflow_tracker import MLflowTracker

                tracker = MLflowTracker(settings.mlflow_tracking_uri)
                agg = _aggregate_metrics(results)
                tracker.log_eval_run(
                    metrics=agg,
                    per_query=results,
                    prompt_versions={"all": "v2"},
                    model_versions={
                        "reason": settings.veris_model_reason or "claude-sonnet-4-6",
                        "answer": settings.veris_model_answer or "claude-sonnet-4-6",
                        "plan": settings.veris_model_plan or "claude-haiku-4-5-20251001",
                    },
                    bench_version="v1",
                )
        except Exception as exc:
            logger.warning("MLflow eval log skipped: %s", exc)

    if results:
        avg = sum(r["faithfulness"] for r in results) / len(results)
        if avg < 0.50:
            logger.warning("Average faithfulness %.3f below 0.50 threshold", avg)
            sys.exit(1)


if __name__ == "__main__":
    main()
