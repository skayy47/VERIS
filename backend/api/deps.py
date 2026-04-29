from __future__ import annotations

import time
from typing import Any

from fastapi import Request

from orchestrator.agent import AsyncAgent
from orchestrator.router import ModelRouter
from orchestrator.tools.citations import CitationExtractorTool
from orchestrator.tools.search import TavilySearchTool
from utils.config import get_settings

_store: dict[str, tuple[Any, float]] = {}
_TTL_SECONDS = 4 * 3600


def build_agent(request: Request) -> AsyncAgent:
    """Construct a fresh AsyncAgent per-request, wired to app.state resources."""
    settings = get_settings()
    episodic = getattr(request.app.state, "episodic", None)
    semantic = getattr(request.app.state, "semantic", None)
    return AsyncAgent(
        settings=settings,
        model_router=ModelRouter(settings),
        search_tool=TavilySearchTool(api_key=settings.tavily_api_key),
        citation_tool=CitationExtractorTool(),
        episodic=episodic,
        semantic=semantic,
    )


def set_session(session_id: str, state: Any) -> None:
    _store[session_id] = (state, time.monotonic())


def get_session(session_id: str) -> Any | None:
    entry = _store.get(session_id)
    if entry is None:
        return None
    state, ts = entry
    if time.monotonic() - ts > _TTL_SECONDS:
        del _store[session_id]
        return None
    return state


def delete_session(session_id: str) -> None:
    _store.pop(session_id, None)


def evict_expired() -> int:
    now = time.monotonic()
    expired = [k for k, (_, ts) in _store.items() if now - ts > _TTL_SECONDS]
    for k in expired:
        del _store[k]
    return len(expired)
