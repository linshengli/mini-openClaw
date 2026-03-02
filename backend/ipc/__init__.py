"""
IPC (Inter-Process Communication) package.
Multi-agent message routing and communication.
"""

from .manager import (
    IPCManager,
    IpcMessage,
    IpcMessageType,
)
from .router import (
    MessageRouter,
    RoutingRule,
)

__all__ = [
    "IPCManager",
    "IpcMessage",
    "IpcMessageType",
    "MessageRouter",
    "RoutingRule",
]
