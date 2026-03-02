"""
Channel utilities.
Common utilities for all channel implementations.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def strip_mentions(content: str) -> str:
    """
    Strip mentions from message content.

    Args:
        content: Message content

    Returns:
        Content with mentions removed
    """
    # Remove Discord mentions: <@123456789>
    content = re.sub(r"<@\d+>", "", content)

    # Remove Discord nickname mentions: <@!123456789>
    content = re.sub(r"<@!\d+>", "", content)

    # Remove Discord role mentions: <@&123456789>
    content = re.sub(r"<@&\d+>", "", content)

    # Remove Telegram/WhatsApp mentions: @username
    content = re.sub(r"@\w+", "", content)

    # Clean up extra whitespace
    content = " ".join(content.split())

    return content


def extract_mentions(content: str) -> List[str]:
    """
    Extract mentioned usernames from content.

    Args:
        content: Message content

    Returns:
        List of mentioned usernames
    """
    mentions = []

    # Discord mentions
    mentions.extend(re.findall(r"<@(\d+)>", content))
    mentions.extend(re.findall(r"<@!(\d+)>", content))
    mentions.extend(re.findall(r"<@&(\d+)>", content))

    # Telegram/WhatsApp mentions
    mentions.extend(re.findall(r"@(\w+)", content))

    return mentions


def format_discord_message(content: str, code_blocks: bool = True) -> str:
    """
    Format message for Discord.

    Args:
        content: Message content
        code_blocks: Whether to use code blocks for formatting

    Returns:
        Formatted message
    """
    if not code_blocks:
        return content

    # Split long messages
    if len(content) > 2000:
        lines = content.split("\n")
        result = []
        current = ""

        for line in lines:
            if len(current) + len(line) + 1 > 2000:
                result.append(current)
                current = line
            else:
                current += "\n" + line if current else line

        if current:
            result.append(current)

        return "\n".join(result)

    return content


def format_telegram_message(content: str, markdown: bool = True) -> str:
    """
    Format message for Telegram.

    Args:
        content: Message content
        markdown: Whether to use Markdown formatting

    Returns:
        Formatted message
    """
    if not markdown:
        return content

    # Telegram Markdown v2 requires escaping certain characters
    # Escape: _ * [ ] ( ) ~ ` > # + - = | { } . !
    if markdown:
        escape_chars = "_[]()~`>+=-.!"
        for char in escape_chars:
            content = content.replace(char, f"\\{char}")

    return content


def format_whatsapp_message(content: str) -> str:
    """
    Format message for WhatsApp.

    Args:
        content: Message content

    Returns:
        Formatted message (WhatsApp has limited formatting)
    """
    # WhatsApp supports: *bold*, _italic_, ~strikethrough~, ```monospace```
    # Convert Markdown to WhatsApp format
    content = re.sub(r"\*\*(.+?)\*\*", r"*\1*", content)  # **bold** -> *bold*
    content = re.sub(r"__(.+?)__", r"_\1_", content)  # __italic__ -> _italic_

    return content


def parse_channel_jid(jid: str) -> Dict[str, str]:
    """
    Parse a channel JID into components.

    Args:
        jid: Channel JID (e.g., "dc:123456789", "tg:-1001234567890")

    Returns:
        Dict with platform and channel_id
    """
    if ":" not in jid:
        return {"platform": "unknown", "channel_id": jid}

    parts = jid.split(":", 1)
    platform = parts[0]
    channel_id = parts[1] if len(parts) > 1 else ""

    # Parse platform-specific IDs
    if platform == "dc":
        # Discord: dc:channel_id or dc:guild_id:channel_id
        sub_parts = channel_id.split(":")
        return {
            "platform": "discord",
            "channel_id": sub_parts[-1],
            "guild_id": sub_parts[0] if len(sub_parts) > 1 else None,
        }
    elif platform == "tg":
        return {"platform": "telegram", "channel_id": channel_id}
    elif platform == "wa":
        return {"platform": "whatsapp", "channel_id": channel_id}
    elif platform == "slack":
        return {"platform": "slack", "channel_id": channel_id}

    return {"platform": platform, "channel_id": channel_id}


def build_channel_jid(platform: str, channel_id: str) -> str:
    """
    Build a channel JID from platform and channel ID.

    Args:
        platform: Platform name (discord, telegram, whatsapp, slack)
        channel_id: Platform-specific channel ID

    Returns:
        Channel JID
    """
    platform_prefixes = {
        "discord": "dc",
        "telegram": "tg",
        "whatsapp": "wa",
        "slack": "slack",
    }

    prefix = platform_prefixes.get(platform, platform)
    return f"{prefix}:{channel_id}"


def truncate_content(content: str, max_length: int = 500) -> str:
    """
    Truncate content to max length with ellipsis.

    Args:
        content: Content to truncate
        max_length: Maximum length

    Returns:
        Truncated content
    """
    if len(content) <= max_length:
        return content

    return content[:max_length - 3] + "..."


def sanitize_text(text: str, max_length: int = 10000) -> str:
    """
    Sanitize text for sending to channels.

    Args:
        text: Text to sanitize
        max_length: Maximum length

    Returns:
        Sanitized text
    """
    # Remove null bytes
    text = text.replace("\x00", "")

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Limit length
    if len(text) > max_length:
        text = truncate_content(text, max_length)

    return text
