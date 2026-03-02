"""
Tests for agents registry and multi-agent system.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import json

from agents.registry import (
    Agent,
    AgentRegistry,
    AgentBackendType,
    AgentRuntime,
    ChannelSubscription,
    get_registry,
)


class TestAgent:
    """Tests for Agent dataclass"""

    def test_create_agent(self):
        """Test creating an agent"""
        agent = Agent(
            id="assistant-1",
            name="Assistant",
            description="A helpful assistant",
            folder="main",
        )
        assert agent.id == "assistant-1"
        assert agent.name == "Assistant"
        assert agent.backend == AgentBackendType.LOCAL
        assert agent.runtime == AgentRuntime.LANGCHAIN

    def test_agent_serialization(self):
        """Test agent to_dict and from_dict"""
        agent = Agent(
            id="test-agent",
            name="Test",
            description="Test agent",
            folder="test",
            is_admin=True,
        )

        data = agent.to_dict()
        restored = Agent.from_dict(data)

        assert restored.id == agent.id
        assert restored.name == agent.name
        assert restored.is_admin == agent.is_admin


class TestChannelSubscription:
    """Tests for ChannelSubscription dataclass"""

    def test_create_subscription(self):
        """Test creating a subscription"""
        sub = ChannelSubscription(
            channel_jid="dc:123456789",
            agent_id="assistant-1",
            trigger="@assistant",
            requires_trigger=True,
            priority=50,
        )
        assert sub.channel_jid == "dc:123456789"
        assert sub.agent_id == "assistant-1"
        assert sub.requires_trigger is True

    def test_subscription_serialization(self):
        """Test subscription to_dict and from_dict"""
        sub = ChannelSubscription(
            channel_jid="tg:chat123",
            agent_id="bot-1",
            trigger="/start",
        )

        data = sub.to_dict()
        restored = ChannelSubscription.from_dict(data)

        assert restored.channel_jid == sub.channel_jid
        assert restored.agent_id == sub.agent_id


class TestAgentRegistry:
    """Tests for AgentRegistry"""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def registry(self, temp_storage):
        """Create a registry with temp storage"""
        return AgentRegistry(storage_dir=temp_storage)

    def test_register_agent(self, registry):
        """Test registering an agent"""
        agent = Agent(id="agent-1", name="Agent One")
        registry.register_agent(agent)

        assert "agent-1" in registry.get_all_agents()
        assert registry.get_agent("agent-1") == agent

    def test_unregister_agent(self, registry):
        """Test unregistering an agent"""
        agent = Agent(id="agent-1", name="Agent One")
        registry.register_agent(agent)

        result = registry.unregister_agent("agent-1")
        assert result is True
        assert "agent-1" not in registry.get_all_agents()

    def test_update_agent(self, registry):
        """Test updating agent attributes"""
        agent = Agent(id="agent-1", name="Agent One")
        registry.register_agent(agent)

        registry.update_agent("agent-1", name="Updated Name")
        updated = registry.get_agent("agent-1")

        assert updated.name == "Updated Name"

    def test_subscribe_to_channel(self, registry):
        """Test subscribing to a channel"""
        agent = Agent(id="agent-1", name="Agent One")
        registry.register_agent(agent)

        sub = ChannelSubscription(
            channel_jid="dc:123",
            agent_id="agent-1",
            trigger="@agent",
        )
        registry.subscribe(sub)

        subscriptions = registry.get_channel_subscriptions("dc:123")
        assert len(subscriptions) == 1
        assert subscriptions[0].agent_id == "agent-1"

    def test_unsubscribe_from_channel(self, registry):
        """Test unsubscribing from a channel"""
        agent = Agent(id="agent-1", name="Agent One")
        registry.register_agent(agent)

        sub = ChannelSubscription(
            channel_jid="dc:123",
            agent_id="agent-1",
            trigger="@agent",
        )
        registry.subscribe(sub)
        registry.unsubscribe("dc:123", "agent-1")

        subscriptions = registry.get_channel_subscriptions("dc:123")
        assert len(subscriptions) == 0

    def test_get_subscribed_agents(self, registry):
        """Test getting agents subscribed to a channel"""
        agent1 = Agent(id="agent-1", name="Agent One")
        agent2 = Agent(id="agent-2", name="Agent Two")
        registry.register_agent(agent1)
        registry.register_agent(agent2)

        sub1 = ChannelSubscription(channel_jid="dc:123", agent_id="agent-1", trigger="@a")
        sub2 = ChannelSubscription(channel_jid="dc:123", agent_id="agent-2", trigger="@b")
        registry.subscribe(sub1)
        registry.subscribe(sub2)

        agents = registry.get_subscribed_agents("dc:123")
        assert len(agents) == 2

    def test_persistence(self, registry, temp_storage):
        """Test agent persistence to disk"""
        agent = Agent(id="agent-1", name="Agent One")
        registry.register_agent(agent)

        # Check file was created
        agents_file = temp_storage / "agents.json"
        assert agents_file.exists()

        # Verify content
        data = json.loads(agents_file.read_text())
        assert len(data["agents"]) == 1
        assert data["agents"][0]["id"] == "agent-1"


class TestGetRegistry:
    """Tests for get_registry helper"""

    def test_get_registry_singleton(self):
        """Test that get_registry returns same instance"""
        from agents import registry as reg_module
        original = reg_module._default_registry
        reg_module._default_registry = None

        try:
            r1 = get_registry()
            r2 = get_registry()
            assert r1 is r2
        finally:
            reg_module._default_registry = original
