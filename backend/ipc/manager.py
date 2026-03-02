"""
IPC Manager for multi-agent communication.
Migrated from OmniClaw's src/ipc.ts

Provides message queuing and inter-agent communication.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from core.paths import STORAGE_DIR


logger = logging.getLogger(__name__)


class IpcMessageType(Enum):
    """Type of IPC message"""
    CHAT_MESSAGE = "chat_message"
    SHARE_REQUEST = "share_request"
    SHARE_RESPONSE = "share_response"
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    BROADCAST = "broadcast"
    STATUS = "status"


@dataclass
class IpcMessage:
    """
    IPC message structure.

    Attributes:
        type: Message type
        source_agent: Sender agent ID
        target_agent: Target agent ID (optional for broadcasts)
        payload: Message payload
        timestamp: ISO format timestamp
        message_id: Unique message ID
        reply_to: ID of message being replied to
        metadata: Additional metadata
    """
    type: IpcMessageType
    source_agent: str
    payload: Dict[str, Any]
    target_agent: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    message_id: str = field(default_factory=lambda: f"msg_{datetime.now().timestamp()}")
    reply_to: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
            "reply_to": self.reply_to,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IpcMessage":
        return cls(
            type=IpcMessageType(data["type"]),
            source_agent=data["source_agent"],
            target_agent=data.get("target_agent"),
            payload=data["payload"],
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            message_id=data.get("message_id", f"msg_{datetime.now().timestamp()}"),
            reply_to=data.get("reply_to"),
            metadata=data.get("metadata", {}),
        )


class IPCManager:
    """
    IPC Manager for multi-agent communication.

    Provides:
    - Message queuing per agent
    - Publish/subscribe messaging
    - Request/response pattern
    - Message persistence (optional)

    Supports two modes:
    - In-memory (default): For single-process deployments
    - Redis-backed: For multi-process deployments
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        storage_dir: Optional[Path] = None,
    ):
        """
        Initialize IPC Manager.

        Args:
            redis_url: Optional Redis URL for distributed messaging
            storage_dir: Optional directory for message persistence
        """
        self.redis_url = redis_url
        self.storage_dir = storage_dir or STORAGE_DIR / "ipc"

        # In-memory queues
        self._queues: Dict[str, asyncio.Queue] = {}
        self._handlers: Dict[IpcMessageType, List[Callable]] = {}
        self._subscribers: Dict[str, Set[str]] = {}  # topic -> agent_ids

        # Message tracking
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._message_count = 0

        # State
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the IPC manager"""
        self._running = True
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info("IPC Manager started")

    async def stop(self) -> None:
        """Stop the IPC manager"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("IPC Manager stopped")

    def register_agent(self, agent_id: str) -> None:
        """Register an agent for receiving messages"""
        if agent_id not in self._queues:
            self._queues[agent_id] = asyncio.Queue()
            logger.info(f"Registered agent: {agent_id}")

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent"""
        if agent_id in self._queues:
            del self._queues[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")

    def register_handler(
        self,
        msg_type: IpcMessageType,
        handler: Callable[[IpcMessage], Any],
    ) -> None:
        """Register a message handler"""
        if msg_type not in self._handlers:
            self._handlers[msg_type] = []
        self._handlers[msg_type].append(handler)
        logger.info(f"Registered handler for {msg_type.value}")

    def subscribe(self, agent_id: str, topic: str) -> None:
        """Subscribe an agent to a topic"""
        if topic not in self._subscribers:
            self._subscribers[topic] = set()
        self._subscribers[topic].add(agent_id)
        logger.info(f"Agent {agent_id} subscribed to {topic}")

    def unsubscribe(self, agent_id: str, topic: str) -> None:
        """Unsubscribe an agent from a topic"""
        if topic in self._subscribers:
            self._subscribers[topic].discard(agent_id)
            logger.info(f"Agent {agent_id} unsubscribed from {topic}")

    async def send_message(
        self,
        message: IpcMessage,
        ensure_delivery: bool = True,
    ) -> bool:
        """
        Send a message to an agent.

        Args:
            message: IPC message to send
            ensure_delivery: Whether to persist for delivery guarantee

        Returns:
            True if message was delivered
        """
        # Ensure source agent is registered
        self.register_agent(message.source_agent)

        # Handle broadcast
        if message.target_agent is None and message.type == IpcMessageType.BROADCAST:
            return await self._broadcast(message)

        # Ensure target agent is registered
        if message.target_agent:
            self.register_agent(message.target_agent)

        # Add to queue
        queue = self._queues.get(message.target_agent)
        if queue:
            await queue.put(message)
            self._message_count += 1

            # Persist if required
            if ensure_delivery:
                await self._persist_message(message)

            logger.debug(f"Message {message.message_id} sent to {message.target_agent}")
            return True

        logger.warning(f"Agent {message.target_agent} not found")
        return False

    async def send_request(
        self,
        message: IpcMessage,
        timeout: float = 30.0,
    ) -> Optional[IpcMessage]:
        """
        Send a request and wait for response.

        Args:
            message: Request message
            timeout: Response timeout in seconds

        Returns:
            Response message or None
        """
        # Create future for response
        response_future: asyncio.Future = asyncio.Future()
        self._pending_responses[message.message_id] = response_future

        # Send request
        await self.send_message(message)

        # Wait for response
        try:
            response = await asyncio.wait_for(response_future, timeout)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Request {message.message_id} timed out")
            return None
        finally:
            self._pending_responses.pop(message.message_id, None)

    async def send_response(
        self,
        request_message: IpcMessage,
        payload: Dict[str, Any],
    ) -> bool:
        """Send a response to a request"""
        response = IpcMessage(
            type=IpcMessageType.SHARE_RESPONSE,
            source_agent=request_message.target_agent or "unknown",
            target_agent=request_message.source_agent,
            payload=payload,
            reply_to=request_message.message_id,
        )
        return await self.send_message(response)

    async def _broadcast(self, message: IpcMessage) -> bool:
        """Broadcast a message to all agents"""
        delivered = False
        for agent_id in self._queues:
            await self._queues[agent_id].put(message)
            delivered = True
        return delivered

    async def _persist_message(self, message: IpcMessage) -> None:
        """Persist message to disk for delivery guarantee"""
        messages_file = self.storage_dir / "pending.json"

        try:
            # Load existing messages
            if messages_file.exists():
                data = json.loads(messages_file.read_text())
            else:
                data = {"messages": []}

            # Add new message
            data["messages"].append(message.to_dict())

            # Save
            messages_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to persist message: {e}")

    async def process_messages(self, agent_id: str, max_messages: int = 100) -> int:
        """
        Process pending messages for an agent.

        Args:
            agent_id: Agent to process messages for
            max_messages: Maximum messages to process

        Returns:
            Number of messages processed
        """
        queue = self._queues.get(agent_id)
        if not queue:
            return 0

        processed = 0
        while processed < max_messages and not queue.empty():
            try:
                message = await asyncio.wait_for(queue.get(), timeout=0.1)
                await self._dispatch_message(message)
                processed += 1
            except asyncio.TimeoutError:
                break

        return processed

    async def _dispatch_message(self, message: IpcMessage) -> None:
        """Dispatch a message to handlers"""
        # Check if this is a response to a pending request
        if message.reply_to and message.reply_to in self._pending_responses:
            future = self._pending_responses[message.reply_to]
            if not future.done():
                future.set_result(message)
            return

        # Call registered handlers
        handlers = self._handlers.get(message.type, [])
        for handler in handlers:
            try:
                result = handler(message)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Handler error: {e}")

    def get_queue_size(self, agent_id: str) -> int:
        """Get pending message count for an agent"""
        queue = self._queues.get(agent_id)
        return queue.qsize() if queue else 0

    def get_stats(self) -> Dict[str, Any]:
        """Get IPC statistics"""
        return {
            "total_messages": self._message_count,
            "registered_agents": len(self._queues),
            "pending_responses": len(self._pending_responses),
            "topics": len(self._subscribers),
        }


# Default IPC manager instance
_default_manager: Optional[IPCManager] = None


def get_ipc_manager() -> IPCManager:
    """Get the default IPC manager"""
    global _default_manager
    if _default_manager is None:
        _default_manager = IPCManager()
    return _default_manager
