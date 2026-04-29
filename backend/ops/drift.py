from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from utils.helpers import get_logger

logger = get_logger(__name__)

_NUMERICAL_COLS = [
    "faithfulness",
    "citation_accuracy",
    "latency_seconds",
    "cost_usd",
    "num_search_hops",
]

_DRIFT_THRESHOLD = 0.15


class DriftMonitor:
    def __init__(self, baseline_path: Path) -> None:
        self._baseline_path = baseline_path

    def _load_baseline(self) -> list[dict[str, Any]] | None:
        if not self._baseline_path.exists():
            logger.warning("Drift baseline not found at %s — skipping comparison", self._baseline_path)
            return None
        rows: list[dict[str, Any]] = []
        with self._baseline_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return rows if rows else None

    def build_report(
        self,
        current_eval_results: list[dict[str, Any]],
        output_path: Path | None = None,
    ) -> dict[str, Any]:
        """Compare current eval results against baseline.

        Returns {drift_score, drifted_columns, alert, baseline_available}.
        If no baseline exists, returns alert=False and baseline_available=False.
        """
        from ops.otel import update_drift_score  # avoid circular at module level

        baseline = self._load_baseline()
        if baseline is None:
            return {
                "drift_score": 0.0,
                "drifted_columns": [],
                "alert": False,
                "baseline_available": False,
            }

        try:
            import pandas as pd  # evidently depends on pandas

            report_data = self._compute_evidently_report(baseline, current_eval_results, output_path)
        except ImportError:
            logger.warning("pandas/evidently not installed — falling back to simple drift")
            report_data = self._simple_drift(baseline, current_eval_results)

        update_drift_score(report_data["drift_score"])
        return report_data

    def _compute_evidently_report(
        self,
        baseline: list[dict[str, Any]],
        current: list[dict[str, Any]],
        output_path: Path | None,
    ) -> dict[str, Any]:
        import pandas as pd

        try:
            from evidently.metric_preset import DataDriftPreset
            from evidently.report import Report
        except ImportError as exc:
            logger.warning("Evidently import failed: %s — using simple drift", exc)
            return self._simple_drift(baseline, current)

        def _to_df(rows: list[dict[str, Any]]) -> pd.DataFrame:
            return pd.DataFrame(
                [
                    {col: row.get(col, 0.0) for col in _NUMERICAL_COLS}
                    for row in rows
                ]
            )

        ref_df = _to_df(baseline)
        cur_df = _to_df(current)

        report = Report(metrics=[DataDriftPreset()])
        try:
            report.run(reference_data=ref_df, current_data=cur_df)
        except Exception as exc:
            logger.warning("Evidently report.run failed: %s", exc)
            return self._simple_drift(baseline, current)

        report_dict = report.as_dict()
        drift_results = report_dict.get("metrics", [{}])[0].get("result", {})
        drift_score = float(drift_results.get("dataset_drift_score", 0.0))
        drifted_columns: list[str] = [
            col
            for col, info in drift_results.get("drift_by_columns", {}).items()
            if info.get("drift_detected", False)
        ]

        if output_path is not None:
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                report.save_html(str(output_path))
                logger.info("Drift HTML report saved to %s", output_path)
            except Exception as exc:
                logger.warning("Failed to save drift HTML: %s", exc)
        elif drift_score > 0:
            date_str = datetime.now().strftime("%Y-%m-%d")
            default_out = Path(__file__).parent.parent / "eval" / "drift" / f"{date_str}.html"
            try:
                default_out.parent.mkdir(parents=True, exist_ok=True)
                report.save_html(str(default_out))
                logger.info("Drift HTML report saved to %s", default_out)
            except Exception as exc:
                logger.warning("Failed to save drift HTML: %s", exc)

        return {
            "drift_score": round(drift_score, 4),
            "drifted_columns": drifted_columns,
            "alert": self.check_alert({"drift_score": drift_score}),
            "baseline_available": True,
        }

    def _simple_drift(
        self,
        baseline: list[dict[str, Any]],
        current: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Fallback: mean absolute deviation of faithfulness as a proxy drift score."""
        def _mean(rows: list[dict[str, Any]], col: str) -> float:
            vals = [r.get(col, 0.0) for r in rows if col in r]
            return sum(vals) / len(vals) if vals else 0.0

        drifted: list[str] = []
        total_deviation = 0.0
        for col in _NUMERICAL_COLS:
            base_mean = _mean(baseline, col)
            cur_mean = _mean(current, col)
            if base_mean == 0:
                continue
            rel_dev = abs(cur_mean - base_mean) / abs(base_mean)
            total_deviation += rel_dev
            if rel_dev > _DRIFT_THRESHOLD:
                drifted.append(col)

        drift_score = round(total_deviation / len(_NUMERICAL_COLS), 4)
        return {
            "drift_score": drift_score,
            "drifted_columns": drifted,
            "alert": self.check_alert({"drift_score": drift_score}),
            "baseline_available": True,
        }

    def check_alert(self, report: dict[str, Any]) -> bool:
        """Return True if drift exceeds threshold."""
        return float(report.get("drift_score", 0.0)) > _DRIFT_THRESHOLD
