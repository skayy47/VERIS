from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from api.deps import build_agent
from api.models import ResearchRequest
from utils.config import get_settings
from utils.helpers import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["research"])


@router.post("/research")
async def research(req: ResearchRequest, request: Request) -> StreamingResponse:
    session_id = str(uuid.uuid4())
    agent = build_agent(request)
    settings = get_settings()

    async def event_stream():
        final_metrics: dict = {}
        try:
            async for update in agent.run(session_id, req.query, req.language):
                yield f"data: {update.model_dump_json()}\n\n"
                if update.is_final:
                    final_metrics = update.metadata.get("metrics", {})
        except Exception as exc:
            logger.error("Stream error session=%s: %s", session_id, exc)
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

        if final_metrics and not settings.testing and settings.mlflow_tracking_uri:
            try:
                from ops.mlflow_tracker import get_tracker

                tracker = get_tracker()
                if tracker:
                    tracker.log_agent_run(
                        session_id=session_id,
                        query=req.query,
                        metrics=final_metrics,
                    )
            except Exception as exc:
                logger.warning("MLflow agent run log failed (non-fatal): %s", exc)

    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)
