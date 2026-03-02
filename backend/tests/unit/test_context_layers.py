"""
Tests for context layer management.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from context.layers import (
    ContextLayer,
    ContextConfig,
    ContextManager,
    ContextBuilder,
    build_context_prompt,
)


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def context_manager(temp_workspace):
    """Create a context manager with temp workspace"""
    return ContextManager(base_dir=temp_workspace)


class TestContextConfig:
    """Tests for ContextConfig dataclass"""

    def test_default_config(self):
        """Test default configuration values"""
        config = ContextConfig()
        assert config.agent_folder is None
        assert config.group_folder is None
        assert config.server_folder is None
        assert config.category_folder is None
        assert config.channel_folder is None

    def test_config_with_values(self):
        """Test configuration with values"""
        config = ContextConfig(
            agent_folder="assistant-1",
            group_folder="main",
            server_folder="servers/discord"
        )
        assert config.agent_folder == "assistant-1"
        assert config.group_folder == "main"
        assert config.server_folder == "servers/discord"


class TestContextManager:
    """Tests for ContextManager"""

    def test_empty_config_returns_empty_layers(self, context_manager):
        """Test that empty config returns empty layer list"""
        config = ContextConfig()
        layers = context_manager.get_context_for_agent(config)
        assert layers == []

    def test_agent_context_layer(self, context_manager, temp_workspace):
        """Test agent context layer creation"""
        # Create agent folder with CLAUDE.md
        agent_dir = temp_workspace / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        (agent_dir / "CLAUDE.md").write_text("# Agent Context\nTest agent")

        config = ContextConfig(agent_folder="test-agent")
        layers = context_manager.get_context_for_agent(config)

        assert len(layers) == 1
        layer = layers[0]
        assert layer.name == "agent"
        assert layer.path == agent_dir
        assert layer.read_only is False

    def test_server_context_is_readonly(self, context_manager, temp_workspace):
        """Test server context is read-only"""
        server_dir = temp_workspace / "servers" / "test-server"
        server_dir.mkdir(parents=True)
        (server_dir / "CLAUDE.md").write_text("# Server Context")

        config = ContextConfig(server_folder="servers/test-server")
        layers = context_manager.get_context_for_agent(config)

        assert len(layers) == 1
        assert layers[0].read_only is True
        assert layers[0].name == "server"

    def test_context_layers_ordered_by_weight(self, context_manager, temp_workspace):
        """Test that layers are ordered from general to specific"""
        # Create all context folders
        server_dir = temp_workspace / "servers" / "srv"
        category_dir = temp_workspace / "category" / "cat"
        agent_dir = temp_workspace / "agents" / "agent"

        for d in [server_dir, category_dir, agent_dir]:
            d.mkdir(parents=True)
            (d / "CLAUDE.md").write_text(f"# Context")

        config = ContextConfig(
            server_folder="servers/srv",
            category_folder="category/cat",
            agent_folder="agent"
        )
        layers = context_manager.get_context_for_agent(config)

        assert len(layers) == 3
        # Should be ordered: server (10) -> category (20) -> agent (50)
        assert layers[0].name == "server"
        assert layers[1].name == "category"
        assert layers[2].name == "agent"

    def test_build_system_prompt(self, context_manager, temp_workspace):
        """Test building system prompt from layers"""
        agent_dir = temp_workspace / "agents" / "test"
        agent_dir.mkdir(parents=True)
        (agent_dir / "CLAUDE.md").write_text("# Agent\nAgent description")

        config = ContextConfig(agent_folder="test")
        layers = context_manager.get_context_for_agent(config)
        prompt = context_manager.build_system_prompt(layers)

        assert "# Agent Context" in prompt
        assert "Agent description" in prompt

    def test_nonexistent_folders_ignored(self, context_manager):
        """Test that non-existent folders are ignored"""
        config = ContextConfig(
            agent_folder="nonexistent",
            group_folder="also-nonexistent"
        )
        layers = context_manager.get_context_for_agent(config)
        assert layers == []

    def test_cache_key_generation(self, context_manager):
        """Test cache key generation from config"""
        config1 = ContextConfig(agent_folder="a1", group_folder="g1")
        config2 = ContextConfig(agent_folder="a1", group_folder="g1")
        config3 = ContextConfig(agent_folder="a2", group_folder="g1")

        key1 = context_manager._make_cache_key(config1)
        key2 = context_manager._make_cache_key(config2)
        key3 = context_manager._make_cache_key(config3)

        assert key1 == key2
        assert key1 != key3

    def test_clear_cache(self, context_manager):
        """Test clearing the context cache"""
        context_manager._context_cache["test"] = ["cached"]
        assert len(context_manager._context_cache) > 0

        context_manager.clear_cache()
        assert len(context_manager._context_cache) == 0


class TestContextManagerFileOperations:
    """Tests for file operations in context layers"""

    def test_read_from_layer(self, context_manager, temp_workspace):
        """Test reading file from layer"""
        agent_dir = temp_workspace / "agents" / "test"
        agent_dir.mkdir(parents=True)
        (agent_dir / "notes.md").write_text("# Notes\nContent")

        config = ContextConfig(agent_folder="test")
        layers = context_manager.get_context_for_agent(config)

        content = context_manager.read_from_layer(layers, "notes.md")
        assert "# Notes" in content
        assert "Content" in content

    def test_write_to_layer(self, context_manager, temp_workspace):
        """Test writing file to writable layer"""
        agent_dir = temp_workspace / "agents" / "test"
        agent_dir.mkdir(parents=True)
        (agent_dir / "CLAUDE.md").write_text("# Agent")

        config = ContextConfig(agent_folder="test")
        layers = context_manager.get_context_for_agent(config)

        success = context_manager.write_to_layer(
            layers[0],
            "new_file.md",
            "# New File\nContent"
        )

        assert success is True
        assert (agent_dir / "new_file.md").exists()

    def test_write_to_readonly_layer_fails(self, context_manager, temp_workspace):
        """Test that writing to read-only layer fails"""
        server_dir = temp_workspace / "servers" / "test"
        server_dir.mkdir(parents=True)
        (server_dir / "CLAUDE.md").write_text("# Server")

        config = ContextConfig(server_folder="servers/test")
        layers = context_manager.get_context_for_agent(config)

        success = context_manager.write_to_layer(
            layers[0],
            "new_file.md",
            "Content"
        )

        assert success is False

    def test_get_layer_file(self, context_manager, temp_workspace):
        """Test getting file path from layer"""
        agent_dir = temp_workspace / "agents" / "test"
        agent_dir.mkdir(parents=True)
        (agent_dir / "config.json").write_text("{}")

        config = ContextConfig(agent_folder="test")
        layers = context_manager.get_context_for_agent(config)

        file_path = context_manager.get_layer_file(layers[0], "config.json")
        assert file_path is not None
        assert file_path.exists()


class TestContextBuilder:
    """Tests for ContextBuilder"""

    def test_builder_with_agent(self):
        """Test building config with agent"""
        config = (ContextBuilder()
                  .with_agent("assistant-1")
                  .build())
        assert config.agent_folder == "assistant-1"

    def test_builder_with_multiple_layers(self):
        """Test building config with multiple layers"""
        config = (ContextBuilder()
                  .with_agent("a1")
                  .with_group("main")
                  .with_server("servers/discord")
                  .with_category("category/support")
                  .build())

        assert config.agent_folder == "a1"
        assert config.group_folder == "main"
        assert config.server_folder == "servers/discord"
        assert config.category_folder == "category/support"

    def test_builder_fluent_interface(self):
        """Test that builder supports fluent interface"""
        builder = ContextBuilder()
        result = builder.with_agent("test")
        assert result is builder  # Should return self


class TestBuildContextPrompt:
    """Tests for build_context_prompt helper function"""

    def test_empty_context_returns_empty_string(self, temp_workspace):
        """Test that empty context returns empty string"""
        # Temporarily change the default workspace
        from context import layers
        original_manager = layers._default_manager
        layers._default_manager = ContextManager(base_dir=temp_workspace)

        try:
            result = build_context_prompt()
            assert result == ""
        finally:
            layers._default_manager = original_manager

    def test_context_with_agent(self, temp_workspace):
        """Test context prompt with agent layer"""
        agent_dir = temp_workspace / "agents" / "test"
        agent_dir.mkdir(parents=True)
        (agent_dir / "CLAUDE.md").write_text("# Test Agent\nDescription")

        from context import layers
        original_manager = layers._default_manager
        layers._default_manager = ContextManager(base_dir=temp_workspace)

        try:
            result = build_context_prompt(agent_id="test")
            assert "# Test Agent" in result
            assert "Description" in result
        finally:
            layers._default_manager = original_manager
