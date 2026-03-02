"""
Tests for IPC manager and message router.
"""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path

from ipc.manager import (
    IPCManager,
    IpcMessage,
    IpcMessageType,
    get_ipc_manager,
)
from ipc.router import (
    MessageRouter,
    RoutingRule,
    get_router,
)
from channels.base import InboundMessage
from agents.registry import Agent, AgentRegistry, ChannelSubscription


class TestIpcMessage:
    """Tests for IpcMessage dataclass"""

    def test_create_message(self):
        """Test creating an IPC message"""
        msg = IpcMessage(
            type=IpcMessageType.CHAT_MESSAGE,
            source_agent="agent-1",
            target_agent="agent-2",
            payload={"content": "Hello"},
        )
        assert msg.type == IpcMessageType.CHAT_MESSAGE
        assert msg.source_agent == "agent-1"
        assert msg.target_agent == "agent-2"

    def test_message_serialization(self):
        """Test message to_dict and from_dict"""
        msg = IpcMessage(
            type=IpcMessageType.SHARE_REQUEST,
            source_agent="agent-1",
            payload={"key": "value"},
        )

        data = msg.to_dict()
        restored = IpcMessage.from_dict(data)

        assert restored.type == msg.type
        assert restored.source_agent == msg.source_agent
        assert restored.payload == msg.payload


class TestIPCManager:
    """Tests for IPCManager"""

    @pytest.fixture
    def ipc_manager(self):
        """Create an IPC manager for testing"""
        return IPCManager()

    @pytest.mark.asyncio
    async def test_start_stop(self, ipc_manager):
        """Test starting and stopping IPC manager"""
        await ipc_manager.start()
        assert ipc_manager._running is True

        await ipc_manager.stop()
        assert ipc_manager._running is False

    def test_register_agent(self, ipc_manager):
        """Test registering an agent"""
        ipc_manager.register_agent("test-agent")
        assert "test-agent" in ipc_manager._queues

    def test_unregister_agent(self, ipc_manager):
        """Test unregistering an agent"""
        ipc_manager.register_agent("test-agent")
        ipc_manager.unregister_agent("test-agent")
        assert "test-agent" not in ipc_manager._queues

    @pytest.mark.asyncio
    async def test_send_message(self, ipc_manager):
        """Test sending a message"""
        await ipc_manager.start()

        ipc_manager.register_agent("agent-1")
        ipc_manager.register_agent("agent-2")

        msg = IpcMessage(
            type=IpcMessageType.CHAT_MESSAGE,
            source_agent="agent-1",
            target_agent="agent-2",
            payload={"content": "Hello"},
        )

        result = await ipc_manager.send_message(msg)
        assert result is True
        assert ipc_manager.get_queue_size("agent-2") == 1

    @pytest.mark.asyncio
    async def test_broadcast(self, ipc_manager):
        """Test broadcasting a message"""
        await ipc_manager.start()

        ipc_manager.register_agent("agent-1")
        ipc_manager.register_agent("agent-2")
        ipc_manager.register_agent("agent-3")

        msg = IpcMessage(
            type=IpcMessageType.BROADCAST,
            source_agent="agent-1",
            payload={"announcement": "Hello all!"},
        )

        result = await ipc_manager.send_message(msg)
        assert result is True

        # All agents should have received the message
        assert ipc_manager.get_queue_size("agent-1") == 1
        assert ipc_manager.get_queue_size("agent-2") == 1
        assert ipc_manager.get_queue_size("agent-3") == 1

    @pytest.mark.asyncio
    async def test_register_handler(self, ipc_manager):
        """Test registering a message handler"""
        received_messages = []

        def handler(msg):
            received_messages.append(msg)

        ipc_manager.register_handler(IpcMessageType.CHAT_MESSAGE, handler)

        await ipc_manager.start()
        ipc_manager.register_agent("agent-1")

        msg = IpcMessage(
            type=IpcMessageType.CHAT_MESSAGE,
            source_agent="system",
            target_agent="agent-1",
            payload={"test": True},
        )

        await ipc_manager.send_message(msg)
        await ipc_manager.process_messages("agent-1")

        assert len(received_messages) == 1

    def test_get_stats(self, ipc_manager):
        """Test getting statistics"""
        ipc_manager.register_agent("agent-1")
        ipc_manager.register_agent("agent-2")

        stats = ipc_manager.get_stats()
        assert stats["registered_agents"] == 2


class TestRoutingRule:
    """Tests for RoutingRule"""

    def test_create_rule(self):
        """Test creating a routing rule"""
        rule = RoutingRule(
            name="test-rule",
            pattern=r"help|assist",
            agent_ids=["assistant-1"],
            priority=10,
        )
        assert rule.name == "test-rule"
        assert rule.matches("I need help") is True
        assert rule.matches("assist me") is True
        assert rule.matches("random text") is False

    def test_rule_case_insensitive(self):
        """Test that rules are case insensitive"""
        rule = RoutingRule(
            name="case-test",
            pattern=r"HELP",
            agent_ids=["assistant-1"],
        )
        assert rule.matches("help") is True
        assert rule.matches("HELP") is True
        assert rule.matches("HeLp") is True


class TestMessageRouter:
    """Tests for MessageRouter"""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for registry"""
        import tempfile
        import shutil
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def registry(self, temp_storage):
        """Create a test registry with isolated storage"""
        return AgentRegistry(storage_dir=temp_storage)

    @pytest.fixture
    def router(self, registry):
        """Create a message router"""
        return MessageRouter(registry=registry)

    def test_add_rule(self, router):
        """Test adding a routing rule"""
        rule = RoutingRule(
            name="test-rule",
            pattern=r"help",
            agent_ids=["agent-1"],
        )
        router.add_rule(rule)
        assert len(router._rules) == 1

    def test_remove_rule(self, router):
        """Test removing a routing rule"""
        rule = RoutingRule(
            name="to-remove",
            pattern=r"test",
            agent_ids=["agent-1"],
        )
        router.add_rule(rule)
        result = router.remove_rule("to-remove")
        assert result is True
        assert len(router._rules) == 0

    def test_register_keyword(self, router):
        """Test registering a keyword trigger"""
        router.register_keyword("help", "agent-kw-1")
        assert "help" in router._keyword_agents
        assert "agent-kw-1" in router._keyword_agents["help"]

    def test_route_message_by_keyword(self, router, registry):
        """Test routing message by keyword"""
        # Register agent and keyword with unique IDs
        agent = Agent(id="kw-assistant", name="Keyword Assistant")
        registry.register_agent(agent)
        router.register_keyword("help", "kw-assistant")

        # Create test message
        msg = InboundMessage(
            id="msg-1",
            chat_jid="dc:123",
            sender="user-1",
            sender_name="User",
            content="I need help with something",
            timestamp=datetime.now().isoformat(),
        )

        # Route message
        targets = router.route_message(msg)
        agent_ids = [t[0] for t in targets]

        assert "kw-assistant" in agent_ids

    def test_route_message_by_rule(self, router, registry):
        """Test routing message by rule"""
        # Register agent with unique ID
        agent = Agent(id="rule-assistant", name="Rule Assistant")
        registry.register_agent(agent)

        # Add rule
        rule = RoutingRule(
            name="help-rule",
            pattern=r"help|assist",
            agent_ids=["rule-assistant"],
        )
        router.add_rule(rule)

        # Create test message
        msg = InboundMessage(
            id="msg-1",
            chat_jid="dc:123",
            sender="user-1",
            sender_name="User",
            content="Can you assist me?",
            timestamp=datetime.now().isoformat(),
        )

        # Route message
        targets = router.route_message(msg)
        agent_ids = [t[0] for t in targets]

        assert "rule-assistant" in agent_ids

    def test_get_routing_stats(self, router):
        """Test getting routing statistics"""
        router.add_rule(RoutingRule(name="r1", pattern="a", agent_ids=["a1"]))
        router.register_keyword("help", "assistant-1")

        stats = router.get_routing_stats()
        assert stats["rules_count"] == 1
        assert stats["keyword_triggers"] == 1


class TestGetRouter:
    """Tests for get_router helper"""

    def test_get_router_singleton(self):
        """Test that get_router returns same instance"""
        from ipc import router as router_module
        original = router_module._default_router
        router_module._default_router = None

        try:
            r1 = get_router()
            r2 = get_router()
            assert r1 is r2
        finally:
            router_module._default_router = original
