"""
Container isolation system for mini-openClaw.
Migrated from OmniClaw's backend system.

Provides:
- Abstract container backend interface
- Local process isolation
- Docker backend (optional)
- Mount security validation
"""

from .base import (
    ContainerBackend,
    ContainerConfig,
    ContainerResult,
    VolumeMount,
    BackendType,
    AgentRuntime,
)
from .local import LocalContainerBackend
from .security import MountSecurity

__all__ = [
    "ContainerBackend",
    "ContainerConfig",
    "ContainerResult",
    "VolumeMount",
    "BackendType",
    "AgentRuntime",
    "LocalContainerBackend",
    "MountSecurity",
]
