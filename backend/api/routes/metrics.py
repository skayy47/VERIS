from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.deps import get_session
from api.models import Metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics/{session_id}", response_model=Metrics)
async def get_metrics(session_id: str) -> Metrics:
    state = get_session(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")
    session_metrics: Metrics | None = getattr(state, "metrics", None)
    if session_metrics is None:
        raise HTTPException(status_code=404, detail="Metrics not yet available")
    return session_metrics
