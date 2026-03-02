"""
Discord channel integration.
Migrated from OmniClaw's src/channels/discord.ts

Uses discord.py for Discord API access.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

import discord
from discord.ext import commands

from .base import Channel, ChatMetadata, InboundMessage, OutboundMessage


logger = logging.getLogger(__name__)


class DiscordChannel(Channel):
    """
    Discord messaging channel.

    Features:
    - Multi-bot support
    - Server/guild context isolation
    - Thread support for streaming output
    - Reaction support
    """

    name = "discord"
    prefix_assistant_name = False

    def __init__(
        self,
        bot_id: str,
        token: str,
        on_message: Callable[[InboundMessage], None],
        on_chat_metadata: Optional[Callable[[ChatMetadata], None]] = None,
        intents: Optional[discord.Intents] = None,
        command_prefix: str = "!",
    ):
        """
        Initialize Discord channel.

        Args:
            bot_id: Bot identifier for routing
            token: Discord bot token
            on_message: Callback for incoming messages
            on_chat_metadata: Optional callback for chat metadata
            intents: Discord intents (default: all needed intents)
            command_prefix: Command prefix for bot
        """
        super().__init__(on_message, on_chat_metadata)

        self.bot_id = bot_id
        self.token = token
        self._connected = False

        # Set up intents
        if intents is None:
            intents = discord.Intents.default()
            intents.message_content = True
            intents.members = True
            intents.guilds = True

        # Create bot
        self.bot = commands.Bot(
            command_prefix=command_prefix,
            intents=intents,
        )

        # Register event handlers
        @self.bot.event
        async def on_ready():
            logger.info(f"Discord bot {self.bot_id} connected as {self.bot.user}")
            self._connected = True

        @self.bot.event
        async def on_message(message: discord.Message):
            await self._handle_message(message)

    async def connect(self) -> None:
        """Connect to Discord"""
        try:
            await self.bot.start(self.token)
        except Exception as e:
            logger.error(f"Failed to connect to Discord: {e}")
            self._connected = False
            raise

    async def disconnect(self) -> None:
        """Disconnect from Discord"""
        if self.bot.is_ready():
            await self.bot.close()
        self._connected = False

    def is_connected(self) -> bool:
        """Check if connected to Discord"""
        return self._connected and self.bot.is_ready()

    def owns_jid(self, jid: str) -> bool:
        """Check if this channel handles this JID"""
        return jid.startswith("dc:")

    async def send_message(
        self,
        jid: str,
        text: str,
        reply_to_message_id: Optional[str] = None,
    ) -> Optional[str]:
        """Send a message to a Discord channel"""
        try:
            channel_id = self._parse_jid(jid)
            channel = self.bot.get_channel(channel_id)

            if channel is None:
                logger.error(f"Channel {channel_id} not found")
                return None

            # Handle reply if specified
            reference = None
            if reply_to_message_id:
                reference = discord.MessageReference(
                    message_id=int(reply_to_message_id),
                    channel_id=channel_id,
                )

            msg = await channel.send(text, reference=reference)
            return str(msg.id)

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return None

    async def send_to_thread(
        self,
        thread_jid: str,
        text: str,
    ) -> Optional[str]:
        """Send a message to a Discord thread"""
        try:
            thread_id = int(thread_jid.replace("dc:thread:", ""))
            thread = self.bot.get_channel(thread_id)

            if thread is None or not isinstance(thread, discord.Thread):
                return None

            msg = await thread.send(text)
            return str(msg.id)

        except Exception as e:
            logger.error(f"Failed to send to thread: {e}")
            return None

    async def create_thread(
        self,
        jid: str,
        message_id: str,
        name: Optional[str] = None,
    ) -> Optional[str]:
        """Create a thread from a message"""
        try:
            channel_id = self._parse_jid(jid)
            channel = self.bot.get_channel(channel_id)

            if channel is None:
                return None

            message = await channel.fetch_message(int(message_id))
            thread = await message.create_thread(
                name=name or "Discussion",
            )

            return f"dc:thread:{thread.id}"

        except Exception as e:
            logger.error(f"Failed to create thread: {e}")
            return None

    async def set_typing(self, jid: str, is_typing: bool) -> None:
        """Show typing indicator"""
        if is_typing:
            channel_id = self._parse_jid(jid)
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.trigger_typing()

    async def send_reaction(
        self,
        jid: str,
        message_id: str,
        emoji: str,
    ) -> bool:
        """Add a reaction to a message"""
        try:
            channel_id = self._parse_jid(jid)
            channel = self.bot.get_channel(channel_id)

            if channel is None:
                return False

            message = await channel.fetch_message(int(message_id))
            await message.add_reaction(emoji)
            return True

        except Exception as e:
            logger.error(f"Failed to add reaction: {e}")
            return False

    async def get_chat_metadata(self, jid: str) -> Optional[ChatMetadata]:
        """Get metadata for a Discord channel"""
        try:
            channel_id = self._parse_jid(jid)
            channel = self.bot.get_channel(channel_id)

            if channel is None:
                return None

            is_group = isinstance(channel, (discord.GroupChannel, discord.DMChannel))
            member_count = None

            if isinstance(channel, discord.GuildChannel):
                member_count = getattr(channel, "member_count", None)

            return ChatMetadata(
                jid=jid,
                name=channel.name if hasattr(channel, "name") else "DM",
                platform="discord",
                is_group=is_group,
                member_count=member_count,
                discord_guild_id=str(channel.guild.id) if hasattr(channel, "guild") and channel.guild else None,
                discord_channel_id=str(channel.id),
            )

        except Exception as e:
            logger.error(f"Failed to get chat metadata: {e}")
            return None

    async def _handle_message(self, message: discord.Message) -> None:
        """Handle incoming Discord message"""
        # Ignore bot messages
        if message.author.bot:
            return

        # Parse mentions
        mentions = [
            {
                "id": str(user.id),
                "name": user.display_name,
                "platform": "discord",
            }
            for user in message.mentions
        ]

        # Create inbound message
        inbound = InboundMessage(
            id=str(message.id),
            chat_jid=f"dc:{message.channel.id}",
            sender=str(message.author.id),
            sender_name=message.author.display_name,
            content=message.content,
            timestamp=message.created_at.isoformat(),
            is_from_me=message.author.id == self.bot.user.id,
            mentions=mentions,
            reply_to_message_id=str(message.reference.message_id) if message.reference else None,
            platform_data={
                "guild_id": str(message.guild.id) if message.guild else None,
                "channel_id": str(message.channel.id),
                "attachments": [
                    {"url": a.url, "filename": a.filename}
                    for a in message.attachments
                ],
            },
        )

        # Call message handler
        self.on_message(inbound)

    def _parse_jid(self, jid: str) -> int:
        """Parse Discord JID to channel ID"""
        # Handle thread JIDs
        if ":thread:" in jid:
            jid = jid.replace("dc:thread:", "")
        else:
            jid = jid.replace("dc:", "")

        # Handle guild:channel format
        if ":" in jid:
            jid = jid.split(":")[-1]

        return int(jid)


def create_discord_channels(
    tokens: Dict[str, str],
    on_message: Callable[[InboundMessage], None],
) -> Dict[str, DiscordChannel]:
    """
    Create multiple Discord channels for multi-bot support.

    Args:
        tokens: Dict of bot_id -> token
        on_message: Message callback

    Returns:
        Dict of bot_id -> DiscordChannel
    """
    channels = {}
    for bot_id, token in tokens.items():
        channel = DiscordChannel(
            bot_id=bot_id,
            token=token,
            on_message=on_message,
        )
        channels[bot_id] = channel

    return channels
