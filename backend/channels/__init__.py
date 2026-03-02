"""
Channels package for mini-openClaw.
Multi-platform messaging integration.
"""

from .base import (
    Channel,
    InboundMessage,
    ChatMetadata,
    OutboundMessage,
)

__all__ = [
    "Channel",
    "InboundMessage",
    "ChatMetadata",
    "OutboundMessage",
]
