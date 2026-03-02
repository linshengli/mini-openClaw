"""
Container backend abstraction layer.
Migrated from OmniClaw's src/backends/types.ts
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class BackendType(Enum):
    """Type of container backend"""
    LOCAL = "local"
    DOCKER = "docker"
    APPLE_CONTAINER = "apple-container"


class AgentRuntime(Enum):
    """Agent runtime environment"""
    LANGCHAIN = "langchain"
    CLAUDE_SDK = "claude-sdk"
    OPENCODE = "opencode"


@dataclass
class VolumeMount:
    """
    Volume mount configuration for containers.

    Attributes:
        host_path: Absolute path on host (supports ~ for home)
        container_path: Path inside container (defaults to basename)
        read_only: Whether mount is read-only (default: True)
    """
    host_path: str
    container_path: Optional[str] = None
    read_only: bool = True

    def __post_init__(self):
        if self.container_path is None:
            self.container_path = Path(self.host_path).name


@dataclass
class ContainerConfig:
    """
    Container configuration.

    Attributes:
        additional_mounts: List of volume mounts
        timeout_ms: Container timeout in milliseconds (default: 300000)
        memory_mb: Container memory in MB (default: 4096)
        network_mode: Network mode - "full" or "none" (default: "none")
        backend_type: Type of backend to use (default: local)
        agent_runtime: Agent runtime to use (default: langchain)
    """
    additional_mounts: List[VolumeMount] = field(default_factory=list)
    timeout_ms: int = 300000  # 5 minutes
    memory_mb: int = 4096
    network_mode: str = "none"
    backend_type: BackendType = BackendType.LOCAL
    agent_runtime: AgentRuntime = AgentRuntime.LANGCHAIN


@dataclass
class ContainerResult:
    """
    Result from running a container.

    Attributes:
        success: Whether execution was successful
        output: Standard output
        error: Standard error
        return_code: Process return code
        duration_ms: Execution duration in milliseconds
    """
    success: bool
    output: str = ""
    error: str = ""
    return_code: int = 0
    duration_ms: int = 0


class ContainerBackend(ABC):
    """
    Abstract base class for container backends.

    Provides isolated execution environment for agents.
    """

    def __init__(self, config: Optional[ContainerConfig] = None):
        self.config = config or ContainerConfig()
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the container backend"""
        pass

    @abstractmethod
    async def run_agent(
        self,
        group_folder: str,
        prompt: str,
        env: Optional[Dict[str, str]] = None,
        on_output: Optional[Callable[[str], None]] = None,
    ) -> ContainerResult:
        """
        Run an agent in an isolated container.

        Args:
            group_folder: Group workspace folder
            prompt: User prompt to process
            env: Environment variables
            on_output: Optional callback for streaming output

        Returns:
            ContainerResult with execution output
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the container backend"""
        pass

    async def __aenter__(self) -> "ContainerBackend":
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.shutdown()
