from __future__ import annotations

"""CLI: python -m eval.drift --current eval/output/latest.json

Compares a eval run against the locked baseline at eval/baseline/v1_baseline.jsonl.
Exits 0 if no alert, 1 if drift score exceeds threshold.
If baseline does not exist yet, exits 0 with a warning (skip-alert mode for Phase 1).
"""

import argparse
import json
import sys
from pathlib import Path

from utils.helpers import get_logger

logger = get_logger(__name__)

_BASELINE = Path(__file__).parent / "baseline" / "v1_baseline.jsonl"


def _load_json(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    # Support both JSON array and JSONL
    text = text.strip()
    if text.startswith("["):
        return json.loads(text)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="VERIS drift detector")
    parser.add_argument(
        "--current",
        required=True,
        help="Path to current eval results JSON (array or JSONL)",
    )
    parser.add_argument(
        "--baseline",
        default=str(_BASELINE),
        help="Path to baseline JSONL (default: eval/baseline/v1_baseline.jsonl)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to write the drift HTML report",
    )
    args = parser.parse_args()

    current_path = Path(args.current)
    if not current_path.exists():
        logger.error("Current eval file not found: %s", current_path)
        sys.exit(2)

    current = _load_json(current_path)
    if not current:
        logger.error("Current eval file is empty: %s", current_path)
        sys.exit(2)

    baseline_path = Path(args.baseline)

    from ops.drift import DriftMonitor

    monitor = DriftMonitor(baseline_path=baseline_path)
    output_path = Path(args.output) if args.output else None
    report = monitor.build_report(current_eval_results=current, output_path=output_path)

    if not report.get("baseline_available"):
        logger.warning(
            "Baseline not found at %s — skipping drift alert (skip-alert mode). "
            "Run a full eval first and save to eval/baseline/v1_baseline.jsonl.",
            baseline_path,
        )
        print(json.dumps({"drift_score": 0.0, "alert": False, "baseline_available": False}))
        sys.exit(0)

    print(json.dumps(report, indent=2))

    if report.get("alert"):
        logger.warning(
            "DRIFT ALERT: score=%.4f > threshold=0.15, drifted_columns=%s",
            report["drift_score"],
            report.get("drifted_columns", []),
        )
        sys.exit(1)

    logger.info(
        "Drift check PASSED: score=%.4f, drifted_columns=%s",
        report["drift_score"],
        report.get("drifted_columns", []),
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
