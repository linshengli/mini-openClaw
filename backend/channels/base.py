"""
Channel abstraction layer.
Migrated from OmniClaw's channel interface.

Provides unified interface for all messaging platforms.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class InboundMessage:
    """
    Inbound message from a channel.

    Attributes:
        id: Platform message ID
        chat_jid: Chat identifier (platform:channel_id)
        sender: Sender identifier
        sender_name: Sender display name
        content: Message content
        timestamp: ISO format timestamp
        is_from_me: Whether message is from bot itself
        mentions: List of mentioned users
        reply_to_message_id: ID of message being replied to (optional)
        platform_data: Raw platform-specific data
    """
    id: str
    chat_jid: str
    sender: str
    sender_name: str
    content: str
    timestamp: str
    is_from_me: bool = False
    mentions: List[Dict[str, str]] = field(default_factory=list)
    reply_to_message_id: Optional[str] = None
    platform_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OutboundMessage:
    """
    Outbound message to a channel.

    Attributes:
        chat_jid: Chat identifier
        content: Message content
        reply_to_message_id: ID of message to reply to
        embed: Optional embed data
        files: Optional file attachments
    """
    chat_jid: str
    content: str
    reply_to_message_id: Optional[str] = None
    embed: Optional[Dict[str, Any]] = None
    files: Optional[List[str]] = None


@dataclass
class ChatMetadata:
    """
    Metadata about a chat/channel.

    Attributes:
        jid: Chat identifier
        name: Chat display name
        platform: Platform name (discord, whatsapp, telegram, slack)
        is_group: Whether this is a group chat
        member_count: Number of members (for groups)
        discord_guild_id: Discord guild ID if applicable
        discord_channel_id: Discord channel ID if applicable
    """
    jid: str
    name: str
    platform: str
    is_group: bool = False
    member_count: Optional[int] = None
    discord_guild_id: Optional[str] = None
    discord_channel_id: Optional[str] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)


class Channel(ABC):
    """
    Abstract base class for messaging channels.

    Provides unified interface for all messaging platforms.
    """

    name: str = "base"
    prefix_assistant_name: bool = True

    def __init__(
        self,
        on_message: Callable[[InboundMessage], None],
        on_chat_metadata: Optional[Callable[[ChatMetadata], None]] = None,
    ):
        """
        Initialize channel.

        Args:
            on_message: Callback for incoming messages
            on_chat_metadata: Optional callback for chat metadata updates
        """
        self.on_message = on_message
        self.on_chat_metadata = on_chat_metadata
        self._connected = False

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the platform"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the platform"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if channel is connected"""
        pass

    @abstractmethod
    def owns_jid(self, jid: str) -> bool:
        """Check if this channel handles this JID"""
        pass

    @abstractmethod
    async def send_message(
        self,
        jid: str,
        text: str,
        reply_to_message_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Send a message to a chat.

        Args:
            jid: Chat identifier
            text: Message text
            reply_to_message_id: ID of message to reply to

        Returns:
            Platform message ID if successful
        """
        pass

    # Optional capabilities

    async def set_typing(self, jid: str, is_typing: bool) -> None:
        """
        Show typing indicator.

        Args:
            jid: Chat identifier
            is_typing: Whether to show typing indicator
        """
        pass

    async def create_thread(
        self,
        jid: str,
        message_id: str,
        name: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a thread for streaming output.

        Args:
            jid: Chat identifier
            message_id: Message to reply to
            name: Thread name

        Returns:
            Thread identifier
        """
        return None

    async def send_to_thread(
        self,
        thread_jid: str,
        text: str,
    ) -> Optional[str]:
        """
        Send message to a thread.

        Args:
            thread_jid: Thread identifier
            text: Message text

        Returns:
            Platform message ID if successful
        """
        return await self.send_message(thread_jid, text)

    async def get_chat_metadata(self, jid: str) -> Optional[ChatMetadata]:
        """
        Get metadata for a chat.

        Args:
            jid: Chat identifier

        Returns:
            ChatMetadata if available
        """
        return None

    async def send_reaction(
        self,
        jid: str,
        message_id: str,
        emoji: str,
    ) -> bool:
        """
        Add a reaction to a message.

        Args:
            jid: Chat identifier
            message_id: Message ID
            emoji: Emoji to react with

        Returns:
            True if successful
        """
        return False

    async def send_file(
        self,
        jid: str,
        file_path: str,
        caption: Optional[str] = None,
    ) -> Optional[str]:
        """
        Send a file to a chat.

        Args:
            jid: Chat identifier
            file_path: Path to file
            caption: Optional caption

        Returns:
            Platform message ID if successful
        """
        return None
