from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.models import StateName
from orchestrator.agent import AsyncAgent
from orchestrator.router import ModelRouter
from orchestrator.tools.citations import CitationExtractorTool
from orchestrator.tools.search import SearchResult, TavilySearchTool


def _llm_response(text: str, input_tokens: int = 10, output_tokens: int = 20) -> MagicMock:
    resp = MagicMock()
    resp.content = [MagicMock(text=text)]
    resp.usage.input_tokens = input_tokens
    resp.usage.output_tokens = output_tokens
    return resp


def _settings(**overrides) -> MagicMock:
    s = MagicMock()
    s.anthropic_api_key = "test-key"
    s.veris_model_plan = ""
    s.veris_model_search = ""
    s.veris_model_reason = ""
    s.veris_model_verify = ""
    s.veris_model_answer = ""
    for k, v in overrides.items():
        setattr(s, k, v)
    return s


_FAKE_RESULT = SearchResult(
    title="Test Title",
    url="https://example.com/1",
    snippet="A test snippet.",
    score=0.9,
)


@pytest.mark.asyncio
async def test_agent_yields_all_states() -> None:
    settings = _settings()
    mock_client = AsyncMock()
    mock_client.messages.create.side_effect = [
        _llm_response('["what is AI?"]'),               # PLAN
        _llm_response("Reasoned synthesis."),           # REASON
        _llm_response("Claims verified."),              # VERIFY
        _llm_response('Answer text.\n{"cited_indices": [1]}'),  # ANSWER
    ]

    search_tool = MagicMock(spec=TavilySearchTool)
    search_tool.run = AsyncMock(return_value=[_FAKE_RESULT])

    with patch("orchestrator.agent.anthropic.AsyncAnthropic", return_value=mock_client):
        agent = AsyncAgent(
            settings=settings,
            model_router=ModelRouter(settings),
            search_tool=search_tool,
            citation_tool=CitationExtractorTool(),
        )
        updates = [u async for u in agent.run("sess-1", "What is AI?", "en")]

    states = [u.state for u in updates]
    assert StateName.PLAN in states
    assert StateName.SEARCH in states
    assert StateName.REASON in states
    assert StateName.VERIFY in states
    assert StateName.ANSWER in states


@pytest.mark.asyncio
async def test_agent_step_indices_are_sequential() -> None:
    settings = _settings()
    mock_client = AsyncMock()
    mock_client.messages.create.return_value = _llm_response('["q1"]')

    search_tool = MagicMock(spec=TavilySearchTool)
    search_tool.run = AsyncMock(return_value=[])

    with patch("orchestrator.agent.anthropic.AsyncAnthropic", return_value=mock_client):
        agent = AsyncAgent(
            settings=settings,
            model_router=ModelRouter(settings),
            search_tool=search_tool,
            citation_tool=CitationExtractorTool(),
        )
        updates = [u async for u in agent.run("sess-2", "query", "fr")]

    indices = [u.step_index for u in updates]
    assert indices == list(range(len(updates)))


@pytest.mark.asyncio
async def test_answer_metadata_contains_metrics_and_citations() -> None:
    settings = _settings()
    mock_client = AsyncMock()
    mock_client.messages.create.side_effect = [
        _llm_response('["q1"]', input_tokens=10, output_tokens=5),
        _llm_response("Reasoning.", input_tokens=200, output_tokens=400),
        _llm_response("Verified.", input_tokens=100, output_tokens=150),
        _llm_response('Answer.\n{"cited_indices": [1]}', input_tokens=300, output_tokens=500),
    ]

    search_tool = MagicMock(spec=TavilySearchTool)
    search_tool.run = AsyncMock(return_value=[_FAKE_RESULT])

    with patch("orchestrator.agent.anthropic.AsyncAnthropic", return_value=mock_client):
        agent = AsyncAgent(
            settings=settings,
            model_router=ModelRouter(settings),
            search_tool=search_tool,
            citation_tool=CitationExtractorTool(),
        )
        updates = [u async for u in agent.run("sess-3", "test", "en")]

    answer = next(u for u in updates if u.state == StateName.ANSWER)
    assert answer.is_final is True
    assert "metrics" in answer.metadata
    assert "citations" in answer.metadata
    assert answer.metadata["metrics"]["tokens_in"] > 0
    assert isinstance(answer.metadata["citations"], list)
