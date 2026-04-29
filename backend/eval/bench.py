from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_BENCH_PATH = Path(__file__).parent / "data" / "veris_bench_v1.jsonl"


def load_bench(
    sample: int | None = None, language: str | None = None
) -> list[dict[str, Any]]:
    """Load benchmark queries from JSONL; optionally filter by language and slice to N rows."""
    rows: list[dict[str, Any]] = []
    with _BENCH_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    if language is not None:
        rows = [r for r in rows if r.get("language") == language]
    if sample is not None:
        rows = rows[:sample]
    return rows
