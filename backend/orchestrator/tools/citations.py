from __future__ import annotations

from urllib.parse import urlparse

from api.models import Citation
from orchestrator.tools.base import Tool
from orchestrator.tools.search import SearchResult
from utils.helpers import get_logger

logger = get_logger(__name__)

_SNIPPET_MAX = 240


class CitationExtractorTool(Tool):
    name = "citation_extractor"
    description = "Extract and rank citations from search results."

    async def run(
        self,
        search_results: list[SearchResult],
        cited_indices: list[int],  # 1-based indices into search_results
    ) -> list[Citation]:
        # Deduplicate by URL, keep highest-scoring duplicate
        seen: dict[str, SearchResult] = {}
        for idx in cited_indices:
            if 1 <= idx <= len(search_results):
                result = search_results[idx - 1]
                if result.url not in seen or result.score > seen[result.url].score:
                    seen[result.url] = result

        sorted_results = sorted(seen.values(), key=lambda r: r.score, reverse=True)

        citations: list[Citation] = []
        for rank, result in enumerate(sorted_results, start=1):
            parsed = urlparse(result.url)
            source = parsed.netloc.removeprefix("www.")
            snippet = result.snippet[:_SNIPPET_MAX]
            citations.append(
                Citation(
                    id=f"c{rank}",
                    rank=rank,
                    title=result.title,
                    url=result.url,
                    source=source,
                    relevance_score=result.score,
                    snippet=snippet,
                )
            )

        logger.debug("Extracted %d citations from %d cited indices", len(citations), len(cited_indices))
        return citations
