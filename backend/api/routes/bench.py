from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from utils.helpers import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["bench"])

_LATEST_PATH = (
    Path(__file__).parent.parent.parent / "eval" / "output" / "latest.json"
)


@router.get("/bench")
async def get_bench_results() -> list[dict[str, Any]]:
    """Return the latest eval run results written by run_eval.py."""
    if not _LATEST_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="No eval results found. Run: python -m eval.run_eval --sample 5",
        )
    try:
        return json.loads(_LATEST_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("Failed to read bench results: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to read bench results") from exc
