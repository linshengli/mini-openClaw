"""
Telegram channel integration.
Migrated from OmniClaw's src/channels/telegram.ts

Uses python-telegram-bot for Telegram API access.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .base import Channel, ChatMetadata, InboundMessage


logger = logging.getLogger(__name__)


class TelegramChannel(Channel):
    """
    Telegram messaging channel.

    Features:
    - Command handling (/chatid, /ping, etc.)
    - Group chat support
    - Reaction support (emoji)
    - Markdown formatting
    """

    name = "telegram"
    prefix_assistant_name = True

    def __init__(
        self,
        bot_token: str,
        on_message: Callable[[InboundMessage], None],
        on_chat_metadata: Optional[Callable[[ChatMetadata], None]] = None,
    ):
        """
        Initialize Telegram channel.

        Args:
            bot_token: Telegram bot token
            on_message: Callback for incoming messages
            on_chat_metadata: Optional callback for chat metadata
        """
        super().__init__(on_message, on_chat_metadata)

        self.bot_token = bot_token
        self._connected = False

        # Create application
        self.application = Application.builder().token(bot_token).build()

        # Register handlers
        self.application.add_handler(CommandHandler("chatid", self._cmd_chatid))
        self.application.add_handler(CommandHandler("ping", self._cmd_ping))
        self.application.add_handler(CommandHandler("start", self._cmd_start))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )

    async def connect(self) -> None:
        """Connect to Telegram"""
        try:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            self._connected = True
            logger.info("Telegram bot connected")
        except Exception as e:
            logger.error(f"Failed to connect to Telegram: {e}")
            self._connected = False
            raise

    async def disconnect(self) -> None:
        """Disconnect from Telegram"""
        if self.application.running:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
        self._connected = False

    def is_connected(self) -> bool:
        """Check if connected to Telegram"""
        return self._connected

    def owns_jid(self, jid: str) -> bool:
        """Check if this channel handles this JID"""
        return jid.startswith("tg:")

    async def send_message(
        self,
        jid: str,
        text: str,
        reply_to_message_id: Optional[str] = None,
    ) -> Optional[str]:
        """Send a message to a Telegram chat"""
        try:
            chat_id = self._parse_jid(jid)

            # Parse reply to message ID from JID format
            reply_to = None
            if reply_to_message_id:
                reply_to = int(reply_to_message_id)

            msg = await self.application.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_to_message_id=reply_to,
                parse_mode="Markdown",
            )
            return str(msg.message_id)

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return None

    async def send_reaction(
        self,
        jid: str,
        message_id: str,
        emoji: str,
    ) -> bool:
        """Add a reaction to a message (Telegram Premium feature)"""
        try:
            chat_id = self._parse_jid(jid)
            await self.application.bot.set_message_reaction(
                chat_id=chat_id,
                message_id=int(message_id),
                reaction=[{"type": "emoji", "emoji": emoji}],
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add reaction: {e}")
            return False

    async def get_chat_metadata(self, jid: str) -> Optional[ChatMetadata]:
        """Get metadata for a Telegram chat"""
        try:
            chat_id = self._parse_jid(jid)
            chat = await self.application.bot.get_chat(chat_id)

            return ChatMetadata(
                jid=jid,
                name=chat.title or chat.first_name or "Unknown",
                platform="telegram",
                is_group=chat.type in ["group", "supergroup", "channel"],
                member_count=chat.get_member_count() if hasattr(chat, "get_member_count") else None,
                extra_data={
                    "chat_type": chat.type,
                    "username": chat.username,
                },
            )

        except Exception as e:
            logger.error(f"Failed to get chat metadata: {e}")
            return None

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming Telegram message"""
        if update.message is None or update.message.text is None:
            return

        message = update.message

        # Parse mentions
        mentions = []
        if message.entities:
            for entity in message.entities:
                if entity.type == "mention":
                    mentioned_user = message.text[entity.offset:entity.offset + entity.length]
                    mentions.append({
                        "id": mentioned_user,
                        "name": mentioned_user,
                        "platform": "telegram",
                    })

        # Create inbound message
        inbound = InboundMessage(
            id=str(message.message_id),
            chat_jid=f"tg:{message.chat_id}",
            sender=str(message.from_user.id) if message.from_user else "unknown",
            sender_name=message.from_user.full_name if message.from_user else "Unknown",
            content=message.text,
            timestamp=message.date.isoformat() if message.date else "",
            is_from_me=False,  # Telegram doesn't send bot's own messages
            mentions=mentions,
            reply_to_message_id=str(message.reply_to_message.message_id) if message.reply_to_message else None,
            platform_data={
                "chat_type": message.chat.type,
                "chat_title": message.chat.title,
            },
        )

        # Call message handler
        self.on_message(inbound)

    async def _cmd_chatid(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /chatid command - returns chat ID"""
        chat_id = f"tg:{update.effective_chat.id}"
        await update.message.reply_text(f"Chat ID: `{chat_id}`", parse_mode="Markdown")

    async def _cmd_ping(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /ping command - returns pong"""
        await update.message.reply_text("Pong!")

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        await update.message.reply_text(
            "Hello! I'm your assistant bot. Send me a message and I'll respond."
        )

    def _parse_jid(self, jid: str) -> int:
        """Parse Telegram JID to chat ID"""
        jid = jid.replace("tg:", "")
        return int(jid)
