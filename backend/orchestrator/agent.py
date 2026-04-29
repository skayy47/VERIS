from __future__ import annotations

import json
import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import anthropic

from api.models import AgentStateUpdate, Citation, Metrics, StateName
from ops.otel import record_run_error, record_run_success, state_span
from orchestrator.router import ModelRouter
from orchestrator.tools.citations import CitationExtractorTool
from orchestrator.tools.search import SearchResult, TavilySearchTool
from utils.config import Settings
from utils.helpers import get_logger

if TYPE_CHECKING:
    from orchestrator.memory.episodic import EpisodicMemory
    from orchestrator.memory.semantic import SemanticMemory

logger = get_logger(__name__)

_MAX_SEARCH_HOPS = 3
_MAX_SEARCH_RESULTS = 15


@dataclass
class _RunState:
    session_id: str
    query: str
    language: str
    t_start: float = field(default_factory=time.monotonic)
    step: int = 0
    plan_queries: list[str] = field(default_factory=list)
    search_results: list[SearchResult] = field(default_factory=list)
    reasoning: str = ""
    verification: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    num_search_hops: int = 0

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.t_start


def _extract_json_array(text: str) -> list[str]:
    """Pull first JSON array of strings from LLM output (fenced or bare)."""
    for pattern in (r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", r"\[[\s\S]*?\]"):
        m = re.search(pattern, text)
        if m:
            candidate = m.group(1) if m.lastindex else m.group(0)
            try:
                result = json.loads(candidate)
                if isinstance(result, list):
                    return [str(x) for x in result if x]
            except json.JSONDecodeError:
                continue
    return []


def _split_answer_and_indices(text: str) -> tuple[str, list[int]]:
    """Split answer prose from trailing cited_indices JSON block."""
    m = re.search(r'\{\s*"cited_indices"\s*:\s*\[[\d,\s]*\]\s*\}', text)
    if m:
        try:
            data = json.loads(m.group(0))
            indices = [int(i) for i in data.get("cited_indices", [])]
            return text[: m.start()].strip(), indices
        except (json.JSONDecodeError, ValueError):
            pass
    return text.strip(), []


class AsyncAgent:
    def __init__(
        self,
        settings: Settings,
        model_router: ModelRouter,
        search_tool: TavilySearchTool,
        citation_tool: CitationExtractorTool,
        episodic: EpisodicMemory | None = None,
        semantic: SemanticMemory | None = None,
    ) -> None:
        self._settings = settings
        self._router = model_router
        self._search = search_tool
        self._citations = citation_tool
        self._episodic = episodic
        self._semantic = semantic
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def _llm(self, model: str, prompt: str, max_tokens: int, run: _RunState) -> str:
        response = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text if response.content else ""
        run.tokens_in += response.usage.input_tokens
        run.tokens_out += response.usage.output_tokens
        run.cost_usd += self._router.estimate_cost_usd(
            model, response.usage.input_tokens, response.usage.output_tokens
        )
        return text

    async def run(
        self, session_id: str, query: str, language: str = "en"
    ) -> AsyncIterator[AgentStateUpdate]:
        run = _RunState(session_id=session_id, query=query, language=language)
        lang_upper = language.upper()

        try:
            # ── PLAN ──────────────────────────────────────────────────────────
            _tok_in, _tok_out, _cost = run.tokens_in, run.tokens_out, run.cost_usd
            with state_span(
                "plan",
                {
                    "veris.state.name": "plan",
                    "veris.session.id": session_id,
                    "veris.model": self._router.select(StateName.PLAN),
                },
            ) as span:
                plan_update = await self._plan(run)
                if span is not None:
                    span.set_attribute("veris.input_tokens", run.tokens_in - _tok_in)
                    span.set_attribute("veris.output_tokens", run.tokens_out - _tok_out)
                    span.set_attribute("veris.cost_usd", run.cost_usd - _cost)
            yield plan_update

            # ── SEARCH ────────────────────────────────────────────────────────
            async for update in self._search_phase(run):
                yield update

            # ── REASON ───────────────────────────────────────────────────────
            _tok_in, _tok_out, _cost = run.tokens_in, run.tokens_out, run.cost_usd
            with state_span(
                "reason",
                {
                    "veris.state.name": "reason",
                    "veris.session.id": session_id,
                    "veris.model": self._router.select(StateName.REASON),
                    "veris.evidence.count": len(run.search_results),
                },
            ) as span:
                reason_update = await self._reason(run)
                if span is not None:
                    span.set_attribute("veris.input_tokens", run.tokens_in - _tok_in)
                    span.set_attribute("veris.output_tokens", run.tokens_out - _tok_out)
                    span.set_attribute("veris.cost_usd", run.cost_usd - _cost)
            yield reason_update

            # ── VERIFY ────────────────────────────────────────────────────────
            _tok_in, _tok_out, _cost = run.tokens_in, run.tokens_out, run.cost_usd
            with state_span(
                "verify",
                {
                    "veris.state.name": "verify",
                    "veris.session.id": session_id,
                    "veris.model": self._router.select(StateName.VERIFY),
                },
            ) as span:
                verify_update = await self._verify(run)
                if span is not None:
                    span.set_attribute("veris.input_tokens", run.tokens_in - _tok_in)
                    span.set_attribute("veris.output_tokens", run.tokens_out - _tok_out)
                    span.set_attribute("veris.cost_usd", run.cost_usd - _cost)
            yield verify_update

            # ── ANSWER ────────────────────────────────────────────────────────
            _tok_in, _tok_out, _cost = run.tokens_in, run.tokens_out, run.cost_usd
            with state_span(
                "answer",
                {
                    "veris.state.name": "answer",
                    "veris.session.id": session_id,
                    "veris.model": self._router.select(StateName.ANSWER),
                },
            ) as span:
                answer_update = await self._answer(run)
                if span is not None:
                    span.set_attribute("veris.input_tokens", run.tokens_in - _tok_in)
                    span.set_attribute("veris.output_tokens", run.tokens_out - _tok_out)
                    span.set_attribute("veris.cost_usd", run.cost_usd - _cost)
            yield answer_update

            record_run_success(
                language=lang_upper,
                latency=run.elapsed,
                cost=run.cost_usd,
            )

        except Exception:
            record_run_error(language=lang_upper)
            raise

    async def _plan(self, run: _RunState) -> AgentStateUpdate:
        model = self._router.select(StateName.PLAN)
        prompt = (
            "You are a research planner. Given a user question, output a JSON array of "
            "3 concise search queries (strings) that together cover the topic.\n\n"
            f"Question: {run.query}\n"
            f"Language: {run.language}\n\n"
            'Output ONLY the JSON array, e.g. ["query 1", "query 2", "query 3"]'
        )
        text = await self._llm(model, prompt, max_tokens=256, run=run)
        queries = _extract_json_array(text) or [run.query]
        run.plan_queries = queries[:_MAX_SEARCH_HOPS]

        step = run.step
        run.step += 1
        logger.info("PLAN %s: %d queries", run.session_id[:8], len(run.plan_queries))
        return AgentStateUpdate(
            session_id=run.session_id,
            state=StateName.PLAN,
            step_index=step,
            content=f"Research plan: {len(run.plan_queries)} search queries generated.",
            metadata={"queries": run.plan_queries},
        )

    async def _search_phase(self, run: _RunState) -> AsyncIterator[AgentStateUpdate]:
        queries = run.plan_queries or [run.query]
        existing_urls: set[str] = set()

        for query in queries:
            hop_num = run.num_search_hops + 1
            with state_span(
                "search",
                {
                    "veris.state.name": "search",
                    "veris.session.id": run.session_id,
                    "veris.search.hops": hop_num,
                },
            ) as span:
                try:
                    results = await self._search.run(query, language=run.language)
                except Exception as exc:
                    logger.warning("Search error for %r: %s", query, exc)
                    results = []
                    if span is not None:
                        try:
                            span.set_attribute("veris.error", str(exc)[:200])
                        except Exception:
                            pass

                new_results = [r for r in results if r.url not in existing_urls]
                existing_urls.update(r.url for r in new_results)
                run.search_results.extend(new_results)
                run.num_search_hops += 1

                if span is not None:
                    span.set_attribute("veris.evidence.count", len(new_results))
                    span.set_attribute("veris.search.hops", run.num_search_hops)

            if len(run.search_results) >= _MAX_SEARCH_RESULTS:
                run.search_results = run.search_results[:_MAX_SEARCH_RESULTS]

            step = run.step
            run.step += 1
            logger.info(
                "SEARCH %s hop=%d new=%d total=%d",
                run.session_id[:8],
                run.num_search_hops,
                len(new_results),
                len(run.search_results),
            )
            yield AgentStateUpdate(
                session_id=run.session_id,
                state=StateName.SEARCH,
                step_index=step,
                content=f'Searched: "{query[:80]}" → {len(new_results)} new results',
                metadata={
                    "query": query,
                    "result_count": len(new_results),
                    "total_results": len(run.search_results),
                    "hop": run.num_search_hops,
                },
            )

    def _format_evidence(self, run: _RunState) -> str:
        lines: list[str] = []
        for i, r in enumerate(run.search_results, start=1):
            lines.append(f"[{i}] {r.title}\n    URL: {r.url}\n    {r.snippet[:300]}")
        return "\n\n".join(lines) if lines else "(no search results)"

    async def _reason(self, run: _RunState) -> AgentStateUpdate:
        model = self._router.select(StateName.REASON)
        evidence_block = self._format_evidence(run)
        prompt = (
            "You are a rigorous research analyst. Synthesize the key findings from the "
            "search results into a coherent reasoning chain. Cite sources using [N] notation.\n\n"
            f"Question: {run.query}\n\n"
            f"Search Results:\n{evidence_block}\n\n"
            "Write a structured reasoning chain (3-5 paragraphs) covering the main claims, "
            "supporting evidence, and any contradictions. Be precise and cite sources by [N]."
        )
        text = await self._llm(model, prompt, max_tokens=1500, run=run)
        run.reasoning = text

        step = run.step
        run.step += 1
        return AgentStateUpdate(
            session_id=run.session_id,
            state=StateName.REASON,
            step_index=step,
            content=text,
            metadata={"evidence_count": len(run.search_results)},
        )

    async def _verify(self, run: _RunState) -> AgentStateUpdate:
        model = self._router.select(StateName.VERIFY)
        evidence_block = self._format_evidence(run)
        prompt = (
            "You are a fact-checker. Verify the reasoning below against the provided sources.\n\n"
            f"Reasoning:\n{run.reasoning}\n\n"
            f"Sources:\n{evidence_block}\n\n"
            "For each key claim, note SUPPORTED / UNSUPPORTED / CONTRADICTED. "
            "Output a concise verification report (2-3 paragraphs)."
        )
        text = await self._llm(model, prompt, max_tokens=800, run=run)
        run.verification = text

        step = run.step
        run.step += 1
        return AgentStateUpdate(
            session_id=run.session_id,
            state=StateName.VERIFY,
            step_index=step,
            content=text,
            metadata={},
        )

    async def _answer(self, run: _RunState) -> AgentStateUpdate:
        model = self._router.select(StateName.ANSWER)
        evidence_block = self._format_evidence(run)
        prompt = (
            "You are a research writer. Compose a clear, accurate, and comprehensive answer "
            "based on the reasoning and verified sources. Cite sources using [N] notation inline.\n\n"
            f"Question: {run.query}\n\n"
            f"Reasoning:\n{run.reasoning}\n\n"
            f"Verification:\n{run.verification}\n\n"
            f"Sources:\n{evidence_block}\n\n"
            "Write the answer (3-5 paragraphs), then on a new line output ONLY this JSON:\n"
            '{"cited_indices": [1, 2, 3]}\n'
            "(replace with the actual 1-based source numbers you cited)"
        )
        text = await self._llm(model, prompt, max_tokens=2000, run=run)
        answer_text, cited_indices = _split_answer_and_indices(text)

        citations: list[Citation] = await self._citations.run(
            run.search_results, cited_indices
        )

        metrics = Metrics(
            faithfulness=None,
            citation_accuracy=None,
            latency_seconds=round(run.elapsed, 2),
            cost_usd=round(run.cost_usd, 6),
            tokens_in=run.tokens_in,
            tokens_out=run.tokens_out,
            citation_count=len(citations),
            num_search_hops=run.num_search_hops,
        )

        if self._episodic is not None:
            try:
                await self._episodic.store(
                    session_id=run.session_id,
                    query=run.query,
                    language=run.language,
                    answer=answer_text,
                    citations=[c.model_dump() for c in citations],
                    metrics=metrics.model_dump(),
                )
            except Exception as exc:
                logger.warning("Episodic store failed (non-fatal): %s", exc)

        step = run.step
        run.step += 1
        logger.info(
            "ANSWER %s: cost=%.5f$ tokens=%d latency=%.1fs citations=%d",
            run.session_id[:8],
            run.cost_usd,
            run.tokens_in + run.tokens_out,
            run.elapsed,
            len(citations),
        )
        return AgentStateUpdate(
            session_id=run.session_id,
            state=StateName.ANSWER,
            step_index=step,
            content=answer_text,
            is_final=True,
            metadata={
                "citations": [c.model_dump() for c in citations],
                "metrics": metrics.model_dump(),
            },
        )
