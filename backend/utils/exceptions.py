from __future__ import annotations


class AgentError(Exception):
    """Base exception for VERIS agent errors."""


class PlanningError(AgentError):
    """Failed to generate a research plan."""


class SearchError(AgentError):
    """Search tool returned no usable results."""


class ReasoningError(AgentError):
    """Model failed to reason over evidence."""


class VerificationError(AgentError):
    """Citation verification failed."""


class ToolError(AgentError):
    """A tool raised an unexpected error."""


class ConfigurationError(AgentError):
    """Missing or invalid configuration."""
