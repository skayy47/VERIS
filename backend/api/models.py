from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class StateName(StrEnum):
    PLAN = "plan"
    SEARCH = "search"
    REASON = "reason"
    VERIFY = "verify"
    ANSWER = "answer"
    DONE = "done"
    ERROR = "error"


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    language: str = Field(default="en", pattern="^[a-z]{2}$")
    max_steps: int = Field(default=8, ge=1, le=20)


class Citation(BaseModel):
    id: str = ""          # stable inline-citation key: c1, c2, …
    rank: int
    title: str
    url: str
    source: str           # derived from netloc, e.g. "arxiv.org"
    relevance_score: float
    snippet: str = ""     # truncated to 240 chars


class Metrics(BaseModel):
    faithfulness: float | None = None
    citation_accuracy: float | None = None
    latency_seconds: float
    cost_usd: float
    tokens_in: int
    tokens_out: int
    citation_count: int | None = None
    num_search_hops: int | None = None


class AgentStateUpdate(BaseModel):
    session_id: str
    state: StateName
    step_index: int
    content: str
    metadata: dict = Field(default_factory=dict)
    is_final: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)
