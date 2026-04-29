from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Iterator

from utils.helpers import get_logger

logger = get_logger(__name__)

_otel_initialized = False
_prom_initialized = False

# Prometheus metric handles — populated by _init_prometheus()
_AGENT_RUNS: Any = None
_STATE_LATENCY: Any = None
_TOTAL_LATENCY: Any = None
_AGENT_COST: Any = None
_ERRORS: Any = None
_EVAL_FAITHFULNESS: Any = None
_EVAL_CITATION_ACCURACY: Any = None
_DRIFT_SCORE: Any = None


def init_tracer(endpoint: str = "http://localhost:4317") -> None:
    global _otel_initialized
    if _otel_initialized:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider()
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

            exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("OTel tracer initialized → %s", endpoint)
        except Exception as exc:
            logger.warning("OTel OTLP exporter skipped: %s", exc)

        trace.set_tracer_provider(provider)
        _otel_initialized = True
    except Exception as exc:
        logger.warning("OTel init skipped: %s", exc)

    _init_prometheus()


def _init_prometheus() -> None:
    global _prom_initialized
    global _AGENT_RUNS, _STATE_LATENCY, _TOTAL_LATENCY, _AGENT_COST
    global _ERRORS, _EVAL_FAITHFULNESS, _EVAL_CITATION_ACCURACY, _DRIFT_SCORE

    if _prom_initialized:
        return
    try:
        from prometheus_client import Counter, Gauge, Histogram

        _AGENT_RUNS = Counter(
            "veris_agent_runs_total",
            "Total agent runs",
            ["status", "language"],
        )
        _STATE_LATENCY = Histogram(
            "veris_agent_state_latency_seconds",
            "Per-state latency in seconds",
            ["state"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
        )
        _TOTAL_LATENCY = Histogram(
            "veris_agent_total_latency_seconds",
            "End-to-end agent latency in seconds",
            ["language"],
            buckets=[1.0, 5.0, 10.0, 20.0, 30.0, 60.0],
        )
        _AGENT_COST = Histogram(
            "veris_agent_cost_usd",
            "Cost per query in USD",
            ["language"],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.5],
        )
        _ERRORS = Counter(
            "veris_agent_errors_total",
            "Agent errors by state and error type",
            ["state", "error_type"],
        )
        _EVAL_FAITHFULNESS = Gauge(
            "veris_eval_faithfulness",
            "Eval faithfulness score by language (last run)",
            ["language"],
        )
        _EVAL_CITATION_ACCURACY = Gauge(
            "veris_eval_citation_accuracy",
            "Eval citation accuracy by language (last run)",
            ["language"],
        )
        _DRIFT_SCORE = Gauge(
            "veris_drift_score",
            "Evidently output drift score from last run",
        )
        _prom_initialized = True
        logger.info("Prometheus metrics initialized")
    except ImportError:
        logger.warning("prometheus_client not installed; Prometheus metrics disabled")
    except Exception as exc:
        logger.warning("Prometheus init failed: %s", exc)


def get_tracer() -> Any:
    try:
        from opentelemetry import trace

        return trace.get_tracer("veris")
    except Exception:
        return None


@contextmanager
def state_span(state_name: str, attributes: dict[str, Any] | None = None) -> Iterator[Any]:
    """Context manager that creates an OTel span for one agent state.

    Yields the span so callers can add post-call attributes (tokens, cost, etc.).
    Also records per-state latency in Prometheus and increments error counters.
    """
    _init_prometheus()
    t0 = time.monotonic()
    tracer = get_tracer()

    span_ctx = tracer.start_as_current_span(f"veris.{state_name}") if tracer else _nullctx()
    with span_ctx as span:
        if attributes and span is not None:
            for k, v in attributes.items():
                try:
                    span.set_attribute(k, v)
                except Exception:
                    pass
        try:
            yield span
        except Exception as exc:
            if span is not None:
                try:
                    span.set_attribute("veris.error", str(exc)[:200])
                except Exception:
                    pass
            if _ERRORS is not None:
                try:
                    _ERRORS.labels(state=state_name, error_type=type(exc).__name__).inc()
                except Exception:
                    pass
            raise
        finally:
            elapsed = time.monotonic() - t0
            if _STATE_LATENCY is not None:
                try:
                    _STATE_LATENCY.labels(state=state_name).observe(elapsed)
                except Exception:
                    pass


def record_run_success(language: str, latency: float, cost: float) -> None:
    _init_prometheus()
    try:
        if _AGENT_RUNS is not None:
            _AGENT_RUNS.labels(status="success", language=language.upper()).inc()
        if _TOTAL_LATENCY is not None:
            _TOTAL_LATENCY.labels(language=language.upper()).observe(latency)
        if _AGENT_COST is not None:
            _AGENT_COST.labels(language=language.upper()).observe(cost)
    except Exception as exc:
        logger.warning("record_run_success failed: %s", exc)


def record_run_error(language: str) -> None:
    _init_prometheus()
    try:
        if _AGENT_RUNS is not None:
            _AGENT_RUNS.labels(status="error", language=language.upper()).inc()
    except Exception as exc:
        logger.warning("record_run_error failed: %s", exc)


def update_eval_gauges(per_language: dict[str, dict[str, float]]) -> None:
    """Update per-language faithfulness and citation accuracy Gauges after an eval run."""
    _init_prometheus()
    for lang, scores in per_language.items():
        try:
            if _EVAL_FAITHFULNESS is not None and "faithfulness" in scores:
                _EVAL_FAITHFULNESS.labels(language=lang.upper()).set(scores["faithfulness"])
            if _EVAL_CITATION_ACCURACY is not None and "citation_accuracy" in scores:
                _EVAL_CITATION_ACCURACY.labels(language=lang.upper()).set(
                    scores["citation_accuracy"]
                )
        except Exception as exc:
            logger.warning("update_eval_gauges failed for %s: %s", lang, exc)


def update_drift_score(score: float) -> None:
    _init_prometheus()
    try:
        if _DRIFT_SCORE is not None:
            _DRIFT_SCORE.set(score)
    except Exception as exc:
        logger.warning("update_drift_score failed: %s", exc)


class _nullctx:
    """Minimal null context that yields None — used when OTel is unavailable."""

    def __enter__(self) -> None:
        return None

    def __exit__(self, *_: object) -> None:
        pass
