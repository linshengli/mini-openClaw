"""
Multi-layer context management system.
Migrated from OmniClaw's context isolation model.

Manages multiple context layers:
- agent: Personal identity and notes (RW)
- category: Team workspace (RW)
- channel: Specific channel context (RW)
- server: Shared server context (RO)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

from core.paths import WORKSPACE_DIR


@dataclass
class ContextLayer:
    """A layer of context with its own storage"""
    name: str
    path: Path
    read_only: bool = False
    description: str = ""
    weight: int = 0  # For ordering when building prompts


@dataclass
class ContextConfig:
    """Configuration for context layers"""
    agent_folder: Optional[str] = None
    category_folder: Optional[str] = None
    channel_folder: Optional[str] = None
    server_folder: Optional[str] = None
    group_folder: Optional[str] = None


class ContextManager:
    """
    Manages multi-layer context for agents.

    Context layers are stacked to provide comprehensive context:
    1. Server context (RO) - shared across all channels in a server
    2. Category context (RW) - team workspace
    3. Channel context (RW) - specific channel state
    4. Agent context (RW) - personal identity and notes
    5. Group context (RW) - group-specific memory
    """

    def __init__(self, base_dir: Path = WORKSPACE_DIR):
        self.base_dir = base_dir
        self._context_cache: Dict[str, List[ContextLayer]] = {}

    def get_context_for_agent(
        self,
        config: ContextConfig
    ) -> List[ContextLayer]:
        """
        Get all context layers for an agent based on configuration.

        Layers are returned in order from most general (server) to most specific (agent).
        """
        layers: List[ContextLayer] = []

        # Server context (RO) - shared across all channels in same server
        if config.server_folder:
            server_dir = self.base_dir / config.server_folder
            if server_dir.exists():
                layers.append(ContextLayer(
                    name="server",
                    path=server_dir,
                    read_only=True,
                    description="Shared server context",
                    weight=10
                ))

        # Category context (RW) - team workspace
        if config.category_folder:
            category_dir = self.base_dir / config.category_folder
            if category_dir.exists():
                layers.append(ContextLayer(
                    name="category",
                    path=category_dir,
                    read_only=False,
                    description="Team workspace",
                    weight=20
                ))

        # Channel context (RW) - specific channel state
        if config.channel_folder:
            channel_dir = self.base_dir / config.channel_folder
            if channel_dir.exists():
                layers.append(ContextLayer(
                    name="channel",
                    path=channel_dir,
                    read_only=False,
                    description="Channel-specific context",
                    weight=30
                ))

        # Group context (RW) - group-specific memory
        if config.group_folder:
            group_dir = self.base_dir / "groups" / config.group_folder
            if group_dir.exists():
                layers.append(ContextLayer(
                    name="group",
                    path=group_dir,
                    read_only=False,
                    description="Group memory",
                    weight=40
                ))

        # Agent context (RW) - personal identity and notes
        if config.agent_folder:
            agent_dir = self.base_dir / "agents" / config.agent_folder
            if agent_dir.exists():
                layers.append(ContextLayer(
                    name="agent",
                    path=agent_dir,
                    read_only=False,
                    description="Agent identity and notes",
                    weight=50
                ))

        # Sort by weight (general to specific)
        layers.sort(key=lambda x: x.weight)

        # Cache the result
        cache_key = self._make_cache_key(config)
        self._context_cache[cache_key] = layers

        return layers

    def _make_cache_key(self, config: ContextConfig) -> str:
        """Create a cache key from config"""
        parts = []
        if config.agent_folder:
            parts.append(f"a:{config.agent_folder}")
        if config.category_folder:
            parts.append(f"c:{config.category_folder}")
        if config.channel_folder:
            parts.append(f"h:{config.channel_folder}")
        if config.server_folder:
            parts.append(f"s:{config.server_folder}")
        if config.group_folder:
            parts.append(f"g:{config.group_folder}")
        return "|".join(parts) if parts else "default"

    def clear_cache(self) -> None:
        """Clear the context cache"""
        self._context_cache.clear()

    def build_system_prompt(self, layers: List[ContextLayer]) -> str:
        """
        Build system prompt from context layers.

        Reads CLAUDE.md from each layer and combines them.
        """
        prompt_parts = []

        for layer in layers:
            claude_md = layer.path / "CLAUDE.md"
            if claude_md.exists():
                content = claude_md.read_text(encoding="utf-8").strip()
                prompt_parts.append(f"# {layer.name.capitalize()} Context\n{content}")

        return "\n\n".join(prompt_parts) if prompt_parts else ""

    def get_layer_file(self, layer: ContextLayer, filename: str) -> Optional[Path]:
        """Get a file from a specific context layer"""
        file_path = layer.path / filename
        if file_path.exists():
            return file_path
        return None

    def write_to_layer(self, layer: ContextLayer, filename: str, content: str) -> bool:
        """
        Write content to a file in a context layer.

        Returns False if layer is read-only.
        """
        if layer.read_only:
            return False

        file_path = layer.path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return True

    def read_from_layer(
        self,
        layers: List[ContextLayer],
        filename: str
    ) -> Optional[str]:
        """
        Read a file from context layers (first match wins).

        Searches from most specific to least specific layer.
        """
        # Search from most specific (highest weight) to least specific
        for layer in reversed(layers):
            file_path = layer.path / filename
            if file_path.exists():
                return file_path.read_text(encoding="utf-8")
        return None


class ContextBuilder:
    """
    Builder for creating ContextConfig from various inputs.
    """

    def __init__(self):
        self._config = ContextConfig()

    def with_agent(self, agent_id: str) -> "ContextBuilder":
        self._config.agent_folder = agent_id
        return self

    def with_group(self, group_name: str) -> "ContextBuilder":
        self._config.group_folder = group_name
        return self

    def with_category(self, category_path: str) -> "ContextBuilder":
        self._config.category_folder = category_path
        return self

    def with_channel(self, channel_path: str) -> "ContextBuilder":
        self._config.channel_folder = channel_path
        return self

    def with_server(self, server_path: str) -> "ContextBuilder":
        self._config.server_folder = server_path
        return self

    def build(self) -> ContextConfig:
        return self._config


# Default context manager instance
_default_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """Get the default context manager instance"""
    global _default_manager
    if _default_manager is None:
        _default_manager = ContextManager()
    return _default_manager


def build_context_prompt(
    agent_id: Optional[str] = None,
    group_folder: Optional[str] = None,
    server_folder: Optional[str] = None,
    category_folder: Optional[str] = None,
    channel_folder: Optional[str] = None
) -> str:
    """
    Build a context prompt from the given configuration.

    This is the main entry point for getting context for an agent.
    """
    manager = get_context_manager()

    config = ContextConfig(
        agent_folder=agent_id,
        group_folder=group_folder,
        server_folder=server_folder,
        category_folder=category_folder,
        channel_folder=channel_folder
    )

    layers = manager.get_context_for_agent(config)
    return manager.build_system_prompt(layers)
