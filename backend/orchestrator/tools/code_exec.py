from __future__ import annotations

from typing import Any

from orchestrator.tools.base import Tool
from utils.helpers import get_logger

logger = get_logger(__name__)


class DockerSandboxTool(Tool):
    name = "docker_sandbox"
    description = "Execute code in an isolated Docker container."

    async def run(self, code: str, language: str = "python") -> dict[str, Any]:
        # TODO(W3): spin up ephemeral container, exec code, return stdout/stderr/exit_code
        return {"stdout": "", "stderr": "", "exit_code": 0}
