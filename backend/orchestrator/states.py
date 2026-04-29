from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from api.models import AgentStateUpdate, Citation, Metrics, StateName


@dataclass
class AgentState:
    query: str
    language: str
    history: list[AgentStateUpdate] = field(default_factory=list)
    current_state: StateName = StateName.PLAN
    evidence: list[dict[str, Any]] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    final_answer: str | None = None
    metrics: Metrics | None = None

    def transition(self, next_state: StateName) -> AgentState:
        self.current_state = next_state
        return self

    def append_evidence(self, item: dict[str, Any]) -> None:
        self.evidence.append(item)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "language": self.language,
            "current_state": self.current_state,
            "evidence_count": len(self.evidence),
            "citations_count": len(self.citations),
            "final_answer": self.final_answer,
        }
