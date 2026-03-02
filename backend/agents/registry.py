"""
Agent registry for multi-agent system.
Migrated from OmniClaw's types.ts Agent interface.

Provides agent registration, discovery, and management.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from core.paths import STORAGE_DIR


logger = logging.getLogger(__name__)


class AgentBackendType(Enum):
    """Type of backend running the agent"""
    LOCAL = "local"
    DOCKER = "docker"
    APPLE_CONTAINER = "apple-container"


class AgentRuntime(Enum):
    """Agent runtime environment"""
    LANGCHAIN = "langchain"
    CLAUDE_SDK = "claude-sdk"
    OPENCODE = "opencode"


@dataclass
class Agent:
    """
    Agent definition.

    Attributes:
        id: Unique agent identifier
        name: Display name
        description: What this agent does
        folder: Agent workspace folder
        backend: Backend type
        runtime: Runtime environment
        is_admin: Whether agent has admin privileges
        server_folder: Shared server context folder
        channel_folder: Channel-specific folder
        category_folder: Category team folder
        created_at: Registration timestamp
        metadata: Additional metadata
    """
    id: str
    name: str
    description: Optional[str] = None
    folder: str = "main"
    backend: AgentBackendType = AgentBackendType.LOCAL
    runtime: AgentRuntime = AgentRuntime.LANGCHAIN
    is_admin: bool = False
    server_folder: Optional[str] = None
    channel_folder: Optional[str] = None
    category_folder: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "folder": self.folder,
            "backend": self.backend.value,
            "runtime": self.runtime.value,
            "is_admin": self.is_admin,
            "server_folder": self.server_folder,
            "channel_folder": self.channel_folder,
            "category_folder": self.category_folder,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Agent":
        """Deserialize from dictionary"""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            folder=data.get("folder", "main"),
            backend=AgentBackendType(data.get("backend", "local")),
            runtime=AgentRuntime(data.get("runtime", "langchain")),
            is_admin=data.get("is_admin", False),
            server_folder=data.get("server_folder"),
            channel_folder=data.get("channel_folder"),
            category_folder=data.get("category_folder"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ChannelSubscription:
    """
    Agent subscription to a channel.

    Migrated from OmniClaw's ChannelSubscription.

    Attributes:
        channel_jid: Channel identifier
        agent_id: Agent subscribing to this channel
        trigger: Trigger word/phrase
        requires_trigger: Whether mention is required
        priority: Subscription priority (lower = higher priority)
        created_at: Subscription timestamp
    """
    channel_jid: str
    agent_id: str
    trigger: str
    requires_trigger: bool = True
    priority: int = 100
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_jid": self.channel_jid,
            "agent_id": self.agent_id,
            "trigger": self.trigger,
            "requires_trigger": self.requires_trigger,
            "priority": self.priority,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChannelSubscription":
        return cls(
            channel_jid=data["channel_jid"],
            agent_id=data["agent_id"],
            trigger=data["trigger"],
            requires_trigger=data.get("requires_trigger", True),
            priority=data.get("priority", 100),
            created_at=data.get("created_at", datetime.now().isoformat()),
        )


class AgentRegistry:
    """
    Registry for agent management.

    Provides:
    - Agent registration
    - Agent discovery
    - Subscription management
    - Persistence
    """

    def __init__(self, storage_dir: Path = STORAGE_DIR / "agents"):
        self.storage_dir = storage_dir
        self._agents: Dict[str, Agent] = {}
        self._subscriptions: Dict[str, List[ChannelSubscription]] = {}  # channel_jid -> subscriptions
        self._agent_subscriptions: Dict[str, Set[str]] = {}  # agent_id -> channel_jids

        # Load persisted data
        self._load_agents()
        self._load_subscriptions()

    def _load_agents(self) -> None:
        """Load agents from disk"""
        agents_file = self.storage_dir / "agents.json"
        if not agents_file.exists():
            return

        try:
            data = json.loads(agents_file.read_text())
            for agent_data in data.get("agents", []):
                agent = Agent.from_dict(agent_data)
                self._agents[agent.id] = agent
            logger.info(f"Loaded {len(self._agents)} agents")
        except Exception as e:
            logger.error(f"Failed to load agents: {e}")

    def _load_subscriptions(self) -> None:
        """Load subscriptions from disk"""
        subs_file = self.storage_dir / "subscriptions.json"
        if not subs_file.exists():
            return

        try:
            data = json.loads(subs_file.read_text())
            for channel_jid, subs_data in data.get("subscriptions", {}).items():
                self._subscriptions[channel_jid] = [
                    ChannelSubscription.from_dict(sub) for sub in subs_data
                ]
            logger.info(f"Loaded subscriptions for {len(self._subscriptions)} channels")
        except Exception as e:
            logger.error(f"Failed to load subscriptions: {e}")

    def _persist_agents(self) -> None:
        """Persist agents to disk"""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        agents_file = self.storage_dir / "agents.json"
        data = {
            "agents": [agent.to_dict() for agent in self._agents.values()],
            "updated_at": datetime.now().isoformat(),
        }
        agents_file.write_text(json.dumps(data, indent=2))

    def _persist_subscriptions(self) -> None:
        """Persist subscriptions to disk"""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        subs_file = self.storage_dir / "subscriptions.json"
        data = {
            "subscriptions": {
                channel_jid: [sub.to_dict() for sub in subs]
                for channel_jid, subs in self._subscriptions.items()
            },
            "updated_at": datetime.now().isoformat(),
        }
        subs_file.write_text(json.dumps(data, indent=2))

    # Agent management

    def register_agent(self, agent: Agent) -> None:
        """Register a new agent"""
        if agent.id in self._agents:
            raise ValueError(f"Agent {agent.id} already registered")

        self._agents[agent.id] = agent
        self._persist_agents()
        logger.info(f"Registered agent: {agent.id}")

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent"""
        if agent_id not in self._agents:
            return False

        del self._agents[agent_id]

        # Clean up subscriptions
        if agent_id in self._agent_subscriptions:
            for channel_jid in self._agent_subscriptions[agent_id]:
                if channel_jid in self._subscriptions:
                    self._subscriptions[channel_jid] = [
                        sub for sub in self._subscriptions[channel_jid]
                        if sub.agent_id != agent_id
                    ]
            del self._agent_subscriptions[agent_id]

        self._persist_agents()
        logger.info(f"Unregistered agent: {agent_id}")
        return True

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        return self._agents.get(agent_id)

    def get_all_agents(self) -> Dict[str, Agent]:
        """Get all registered agents"""
        return self._agents.copy()

    def update_agent(self, agent_id: str, **kwargs) -> bool:
        """Update agent attributes"""
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        for key, value in kwargs.items():
            if hasattr(agent, key):
                setattr(agent, key, value)

        self._persist_agents()
        return True

    # Subscription management

    def subscribe(self, subscription: ChannelSubscription) -> None:
        """Add a channel subscription"""
        channel_jid = subscription.channel_jid

        if channel_jid not in self._subscriptions:
            self._subscriptions[channel_jid] = []

        # Check for existing subscription
        for i, sub in enumerate(self._subscriptions[channel_jid]):
            if sub.agent_id == subscription.agent_id:
                # Update existing
                self._subscriptions[channel_jid][i] = subscription
                self._persist_subscriptions()
                return

        # Add new subscription
        self._subscriptions[channel_jid].append(subscription)

        # Update agent's channel list
        if subscription.agent_id not in self._agent_subscriptions:
            self._agent_subscriptions[subscription.agent_id] = set()
        self._agent_subscriptions[subscription.agent_id].add(channel_jid)

        self._persist_subscriptions()
        logger.info(f"Added subscription: {subscription.agent_id} -> {channel_jid}")

    def unsubscribe(self, channel_jid: str, agent_id: str) -> bool:
        """Remove a channel subscription"""
        if channel_jid not in self._subscriptions:
            return False

        original_len = len(self._subscriptions[channel_jid])
        self._subscriptions[channel_jid] = [
            sub for sub in self._subscriptions[channel_jid]
            if sub.agent_id != agent_id
        ]

        # Clean up agent's channel list
        if agent_id in self._agent_subscriptions:
            self._agent_subscriptions[agent_id].discard(channel_jid)

        self._persist_subscriptions()
        return len(self._subscriptions[channel_jid]) < original_len

    def get_channel_subscriptions(self, channel_jid: str) -> List[ChannelSubscription]:
        """Get all subscriptions for a channel"""
        return self._subscriptions.get(channel_jid, [])

    def get_agent_subscriptions(self, agent_id: str) -> List[str]:
        """Get all channels an agent is subscribed to"""
        channel_jids = self._agent_subscriptions.get(agent_id, set())
        return list(channel_jids)

    def get_subscribed_agents(self, channel_jid: str) -> List[Agent]:
        """Get all agents subscribed to a channel"""
        subscriptions = self.get_channel_subscriptions(channel_jid)
        agents = []
        for sub in subscriptions:
            agent = self.get_agent(sub.agent_id)
            if agent:
                agents.append(agent)
        # Sort by priority
        agents.sort(key=lambda a: next(
            (sub.priority for sub in subscriptions if sub.agent_id == a.id),
            100
        ))
        return agents


# Default registry instance
_default_registry: Optional[AgentRegistry] = None


def get_registry() -> AgentRegistry:
    """Get the default agent registry"""
    global _default_registry
    if _default_registry is None:
        _default_registry = AgentRegistry()
    return _default_registry
