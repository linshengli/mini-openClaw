"""
Message router for multi-agent system.
Migrated from OmniClaw's routing logic.

Provides message routing based on subscriptions and triggers.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from agents.registry import Agent, AgentRegistry, ChannelSubscription, get_registry
from channels.base import InboundMessage


logger = logging.getLogger(__name__)


@dataclass
class RoutingRule:
    """
    Message routing rule.

    Attributes:
        name: Rule name
        pattern: Regex pattern for matching content
        agent_ids: List of agent IDs to route to
        priority: Rule priority (higher = processed first)
        requires_mention: Whether rule requires agent mention
        channels: List of channel JIDs this rule applies to
    """
    name: str
    pattern: str
    agent_ids: List[str]
    priority: int = 0
    requires_mention: bool = False
    channels: List[str] = field(default_factory=list)
    _compiled_pattern: re.Pattern = field(init=False)

    def __post_init__(self):
        self._compiled_pattern = re.compile(self.pattern, re.IGNORECASE)

    def matches(self, content: str) -> bool:
        """Check if content matches this rule"""
        return bool(self._compiled_pattern.search(content))


class MessageRouter:
    """
    Message router for multi-agent system.

    Routes incoming messages to appropriate agents based on:
    - Channel subscriptions
    - Trigger mentions
    - Routing rules
    - Keywords
    """

    def __init__(self, registry: Optional[AgentRegistry] = None):
        """
        Initialize message router.

        Args:
            registry: Agent registry (uses default if not provided)
        """
        self.registry = registry or get_registry()
        self._rules: List[RoutingRule] = []
        self._keyword_agents: Dict[str, Set[str]] = {}  # keyword -> agent_ids

    def add_rule(self, rule: RoutingRule) -> None:
        """Add a routing rule"""
        self._rules.append(rule)
        # Sort by priority (descending)
        self._rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"Added routing rule: {rule.name}")

    def remove_rule(self, name: str) -> bool:
        """Remove a routing rule by name"""
        for i, rule in enumerate(self._rules):
            if rule.name == name:
                del self._rules[i]
                logger.info(f"Removed routing rule: {name}")
                return True
        return False

    def register_keyword(self, keyword: str, agent_id: str) -> None:
        """Register a keyword trigger for an agent"""
        keyword_lower = keyword.lower()
        if keyword_lower not in self._keyword_agents:
            self._keyword_agents[keyword_lower] = set()
        self._keyword_agents[keyword_lower].add(agent_id)
        logger.info(f"Registered keyword {keyword} for agent {agent_id}")

    def unregister_keyword(self, keyword: str, agent_id: str) -> None:
        """Unregister a keyword trigger"""
        keyword_lower = keyword.lower()
        if keyword_lower in self._keyword_agents:
            self._keyword_agents[keyword_lower].discard(agent_id)
            if not self._keyword_agents[keyword_lower]:
                del self._keyword_agents[keyword_lower]
            logger.info(f"Unregistered keyword {keyword} for agent {agent_id}")

    def route_message(
        self,
        message: InboundMessage,
        include_all_subscribed: bool = False,
    ) -> List[Tuple[str, str]]:
        """
        Route a message to appropriate agents.

        Args:
            message: Incoming message to route
            include_all_subscribed: If True, include all subscribed agents

        Returns:
            List of (agent_id, reason) tuples
        """
        targets: Dict[str, str] = {}  # agent_id -> reason

        # Check routing rules first (highest priority)
        for rule in self._rules:
            # Check channel filter
            if rule.channels and message.chat_jid not in rule.channels:
                continue

            # Check mention requirement
            if rule.requires_mention and not self._is_mentioned(message, rule.agent_ids):
                continue

            # Check pattern match
            if rule.matches(message.content):
                for agent_id in rule.agent_ids:
                    if agent_id not in targets:
                        targets[agent_id] = f"rule:{rule.name}"

        # Check keyword triggers
        content_lower = message.content.lower()
        for keyword, agent_ids in self._keyword_agents.items():
            if keyword in content_lower:
                for agent_id in agent_ids:
                    if agent_id not in targets:
                        targets[agent_id] = f"keyword:{keyword}"

        # Check subscriptions if enabled
        if include_all_subscribed:
            subscribed_agents = self.registry.get_subscribed_agents(message.chat_jid)
            for agent in subscribed_agents:
                if agent.id not in targets:
                    targets[agent.id] = "subscription"

        # Check for direct mentions
        mentioned_agents = self._extract_mentions(message)
        for agent_id in mentioned_agents:
            if agent_id not in targets:
                targets[agent_id] = "mention"

        return list(targets.items())

    def _is_mentioned(self, message: InboundMessage, agent_ids: List[str]) -> bool:
        """Check if any of the agents are mentioned"""
        mentioned = self._extract_mentions(message)
        return any(aid in mentioned for aid in agent_ids)

    def _extract_mentions(self, message: InboundMessage) -> List[str]:
        """Extract agent IDs from mentions"""
        agent_ids = []

        # Check platform mentions
        for mention in message.mentions:
            # Try to match mention name to agent ID
            name = mention.get("name", "").lower()
            agent_id = mention.get("id", "")

            # Check if any agent has this name
            for agent in self.registry.get_all_agents().values():
                if agent.name.lower() == name or agent.id == agent_id:
                    agent_ids.append(agent.id)

        # Check content for @mentions
        content = message.content
        for match in re.finditer(r"@(\w+)", content):
            mention_name = match.group(1).lower()
            for agent in self.registry.get_all_agents().values():
                if agent.name.lower() == mention_name:
                    agent_ids.append(agent.id)

        return agent_ids

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        return {
            "rules_count": len(self._rules),
            "keyword_triggers": len(self._keyword_agents),
            "registered_agents": len(self.registry.get_all_agents()),
        }


# Default router instance
_default_router: Optional[MessageRouter] = None


def get_router() -> MessageRouter:
    """Get the default message router"""
    global _default_router
    if _default_router is None:
        _default_router = MessageRouter()
    return _default_router
