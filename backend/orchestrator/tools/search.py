from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from orchestrator.tools.base import Tool
from utils.helpers import get_logger

logger = get_logger(__name__)

_RAW_CONTENT_MAX = 8_000


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    score: float
    raw_content: str | None = None


class TavilySearchTool(Tool):
    name = "tavily_search"
    description = "Search the web for research-grade results"

    def __init__(self, api_key: str, max_results: int = 5) -> None:
        self._api_key = api_key
        self._max_results = max_results

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def run(
        self,
        query: str,
        language: str = "en",
        search_depth: Literal["basic", "advanced"] = "advanced",
    ) -> list[SearchResult]:
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=self._api_key)
        t0 = time.monotonic()

        # Bias Tavily toward the target language for non-English queries
        effective_query = f"[{language.upper()}] {query}" if language.lower() != "en" else query

        try:
            response = await client.search(
                query=effective_query,
                search_depth=search_depth,
                max_results=self._max_results,
                include_answer=False,
                include_raw_content=True,
            )
        except Exception as exc:
            msg = str(exc).lower()
            if "401" in str(exc) or "unauthorized" in msg or "invalid api key" in msg:
                raise RuntimeError(
                    f"Tavily auth error — verify TAVILY_API_KEY in .env: {exc}"
                ) from exc
            raise

        latency_ms = (time.monotonic() - t0) * 1000
        results = response.get("results", [])

        logger.info(
            "Tavily search: query=%r results=%d latency_ms=%.0f",
            query[:80],
            len(results),
            latency_ms,
        )

        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("content", ""),
                score=float(r.get("score", 0.0)),
                raw_content=(r.get("raw_content") or "")[:_RAW_CONTENT_MAX] or None,
            )
            for r in results
        ]
