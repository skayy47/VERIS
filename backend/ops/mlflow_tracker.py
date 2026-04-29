from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any

from utils.helpers import get_logger

if TYPE_CHECKING:
    from eval.metrics import EvalMetrics

logger = get_logger(__name__)


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return "unknown"


class MLflowTracker:
    def __init__(
        self,
        tracking_uri: str,
        experiment_name: str = "veris-eval",
    ) -> None:
        self._tracking_uri = tracking_uri
        self._experiment_name = experiment_name
        self._ready = bool(tracking_uri)

    def _ensure_mlflow(self) -> Any:
        if not self._ready:
            return None
        try:
            import mlflow  # lazy — heavy dep

            mlflow.set_tracking_uri(self._tracking_uri)
            mlflow.set_experiment(self._experiment_name)
            return mlflow
        except Exception as exc:
            logger.warning("MLflow unavailable: %s", exc)
            return None

    def log_eval_run(
        self,
        metrics: EvalMetrics,
        per_query: list[dict[str, Any]],
        prompt_versions: dict[str, str],
        model_versions: dict[str, str],
        bench_version: str = "v1",
        git_sha: str = "",
    ) -> str | None:
        """Log a full benchmark eval run. Returns mlflow run_id or None."""
        mlflow = self._ensure_mlflow()
        if mlflow is None:
            return None
        try:
            import json
            import tempfile
            from pathlib import Path

            with mlflow.start_run() as run:
                # Aggregate metrics
                mlflow.log_metrics(
                    {
                        "faithfulness": metrics.faithfulness,
                        "citation_accuracy": metrics.citation_accuracy,
                        "latency_seconds": metrics.latency_seconds,
                        "cost_usd": metrics.cost_usd,
                        "tokens_in": float(metrics.tokens_in),
                        "tokens_out": float(metrics.tokens_out),
                        "citation_count": float(metrics.citation_count),
                        "num_search_hops": float(metrics.num_search_hops),
                    }
                )
                # Prompt + model versions as params
                for k, v in prompt_versions.items():
                    mlflow.log_param(f"prompt_{k}", v[:250])
                for k, v in model_versions.items():
                    mlflow.log_param(f"model_{k}", v[:250])

                mlflow.set_tags(
                    {
                        "bench_version": bench_version,
                        "git_sha": git_sha or _git_sha(),
                        "query_count": str(len(per_query)),
                    }
                )

                # Per-query results as artifact
                with tempfile.TemporaryDirectory() as tmp:
                    artifact_path = Path(tmp) / "per_query.json"
                    artifact_path.write_text(
                        json.dumps(per_query, indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    mlflow.log_artifact(str(artifact_path), artifact_path="eval")

                logger.info(
                    "MLflow eval run logged: id=%s faithfulness=%.3f",
                    run.info.run_id,
                    metrics.faithfulness,
                )
                return run.info.run_id
        except Exception as exc:
            logger.warning("MLflow eval log failed: %s", exc)
            return None

    def log_agent_run(
        self,
        session_id: str,
        query: str,
        metrics: dict[str, Any],
    ) -> None:
        """Lightweight production-traffic log — cost, latency, faithfulness_self."""
        mlflow = self._ensure_mlflow()
        if mlflow is None:
            return
        try:
            with mlflow.start_run(run_name=f"prod-{session_id[:8]}"):
                mlflow.log_param("session_id", session_id)
                mlflow.log_param("query_preview", query[:120])
                numeric_keys = {
                    "cost_usd",
                    "latency_seconds",
                    "tokens_in",
                    "tokens_out",
                    "citation_count",
                    "num_search_hops",
                }
                mlflow.log_metrics(
                    {k: float(v) for k, v in metrics.items() if k in numeric_keys and v is not None}
                )
        except Exception as exc:
            logger.warning("MLflow agent run log failed: %s", exc)


_tracker: MLflowTracker | None = None


def get_tracker() -> MLflowTracker | None:
    """Return module-level tracker instance, initialised once."""
    global _tracker
    if _tracker is None:
        try:
            from utils.config import get_settings

            s = get_settings()
            if s.mlflow_tracking_uri:
                _tracker = MLflowTracker(s.mlflow_tracking_uri)
        except Exception as exc:
            logger.warning("MLflowTracker init failed: %s", exc)
    return _tracker
