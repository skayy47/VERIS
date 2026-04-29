from __future__ import annotations

from api.models import StateName
from utils.config import Settings
from utils.helpers import get_logger

logger = get_logger(__name__)

_SONNET = "claude-sonnet-4-6"
_HAIKU = "claude-haiku-4-5-20251001"

# TODO(2026-04-25): verify pricing at https://www.anthropic.com/pricing
# USD per 1 million tokens: (input_price, output_price)
_COST_PER_M: dict[str, tuple[float, float]] = {
    _SONNET: (3.00, 15.00),
    _HAIKU: (0.80, 4.00),
}

_DEFAULT_MAP: dict[StateName, str] = {
    StateName.PLAN: _HAIKU,
    StateName.SEARCH: _HAIKU,    # search-decide hops use Haiku
    StateName.REASON: _SONNET,
    StateName.VERIFY: _SONNET,
    StateName.ANSWER: _SONNET,
}


class ModelRouter:
    def __init__(self, settings: Settings) -> None:
        self._map: dict[StateName, str] = {
            StateName.PLAN: settings.veris_model_plan or _HAIKU,
            StateName.SEARCH: settings.veris_model_search or _HAIKU,
            StateName.REASON: settings.veris_model_reason or _SONNET,
            StateName.VERIFY: settings.veris_model_verify or _SONNET,
            StateName.ANSWER: settings.veris_model_answer or _SONNET,
        }

    def select(self, state: StateName) -> str:
        """Return the Claude model id for the given agent state."""
        return self._map.get(state, _SONNET)

    def estimate_cost_usd(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate USD cost for a single Anthropic API call."""
        prices = _COST_PER_M.get(model, (3.00, 15.00))
        return (input_tokens * prices[0] + output_tokens * prices[1]) / 1_000_000
