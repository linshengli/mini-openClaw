"""
Tests for channels base and utilities.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from channels.base import (
    Channel,
    InboundMessage,
    OutboundMessage,
    ChatMetadata,
)
from channels.utils import (
    strip_mentions,
    extract_mentions,
    parse_channel_jid,
    build_channel_jid,
    truncate_content,
    sanitize_text,
)


class TestInboundMessage:
    """Tests for InboundMessage dataclass"""

    def test_create_message(self):
        """Test creating an inbound message"""
        msg = InboundMessage(
            id="msg_123",
            chat_jid="dc:123456789",
            sender="user_456",
            sender_name="Test User",
            content="Hello, World!",
            timestamp=datetime.now().isoformat(),
        )
        assert msg.id == "msg_123"
        assert msg.chat_jid == "dc:123456789"
        assert msg.is_from_me is False
        assert msg.mentions == []


class TestOutboundMessage:
    """Tests for OutboundMessage dataclass"""

    def test_create_message(self):
        """Test creating an outbound message"""
        msg = OutboundMessage(
            chat_jid="dc:123456789",
            content="Response",
        )
        assert msg.chat_jid == "dc:123456789"
        assert msg.content == "Response"
        assert msg.reply_to_message_id is None


class TestChatMetadata:
    """Tests for ChatMetadata dataclass"""

    def test_create_metadata(self):
        """Test creating chat metadata"""
        meta = ChatMetadata(
            jid="dc:123456789",
            name="general",
            platform="discord",
            is_group=True,
            member_count=100,
        )
        assert meta.jid == "dc:123456789"
        assert meta.name == "general"
        assert meta.is_group is True
        assert meta.member_count == 100


class TestChannel:
    """Tests for Channel abstract class"""

    def test_channel_is_abstract(self):
        """Test that Channel is abstract"""
        with pytest.raises(TypeError):
            Channel(on_message=lambda x: x)


class TestStripMentions:
    """Tests for strip_mentions utility"""

    def test_strip_discord_mentions(self):
        """Test stripping Discord mentions"""
        content = "Hello <@123456789> and <@!987654321>!"
        result = strip_mentions(content)
        assert result == "Hello and !"

    def test_strip_role_mentions(self):
        """Test stripping role mentions"""
        content = "Ping <@&111222333>!"
        result = strip_mentions(content)
        assert result == "Ping !"

    def test_strip_username_mentions(self):
        """Test stripping username mentions"""
        content = "Hey @user123, check this out!"
        result = strip_mentions(content)
        assert result == "Hey , check this out!"

    def test_strip_multiple_mentions(self):
        """Test stripping multiple mentions"""
        content = "@alice @bob @charlie let's go"
        result = strip_mentions(content)
        assert result == "let's go"


class TestExtractMentions:
    """Tests for extract_mentions utility"""

    def test_extract_discord_mentions(self):
        """Test extracting Discord mentions"""
        content = "Hello <@123456789>!"
        result = extract_mentions(content)
        assert "123456789" in result

    def test_extract_username_mentions(self):
        """Test extracting username mentions"""
        content = "Hey @user123!"
        result = extract_mentions(content)
        assert "user123" in result


class TestParseChannelJid:
    """Tests for parse_channel_jid utility"""

    def test_parse_discord_jid(self):
        """Test parsing Discord JID"""
        result = parse_channel_jid("dc:123456789")
        assert result["platform"] == "discord"
        assert result["channel_id"] == "123456789"

    def test_parse_telegram_jid(self):
        """Test parsing Telegram JID"""
        result = parse_channel_jid("tg:-1001234567890")
        assert result["platform"] == "telegram"
        assert result["channel_id"] == "-1001234567890"

    def test_parse_whatsapp_jid(self):
        """Test parsing WhatsApp JID"""
        result = parse_channel_jid("wa:1234567890@s.whatsapp.net")
        assert result["platform"] == "whatsapp"
        assert result["channel_id"] == "1234567890@s.whatsapp.net"


class TestBuildChannelJid:
    """Tests for build_channel_jid utility"""

    def test_build_discord_jid(self):
        """Test building Discord JID"""
        result = build_channel_jid("discord", "123456789")
        assert result == "dc:123456789"

    def test_build_telegram_jid(self):
        """Test building Telegram JID"""
        result = build_channel_jid("telegram", "-1001234567890")
        assert result == "tg:-1001234567890"

    def test_build_whatsapp_jid(self):
        """Test building WhatsApp JID"""
        result = build_channel_jid("whatsapp", "1234567890")
        assert result == "wa:1234567890"


class TestTruncateContent:
    """Tests for truncate_content utility"""

    def test_truncate_short_content(self):
        """Test truncating short content"""
        result = truncate_content("Hello", max_length=100)
        assert result == "Hello"

    def test_truncate_long_content(self):
        """Test truncating long content"""
        content = "A" * 1000
        result = truncate_content(content, max_length=100)
        assert len(result) == 100
        assert result.endswith("...")


class TestSanitizeText:
    """Tests for sanitize_text utility"""

    def test_remove_null_bytes(self):
        """Test removing null bytes"""
        result = sanitize_text("Hello\x00World")
        assert "\x00" not in result

    def test_normalize_line_endings(self):
        """Test normalizing line endings"""
        result = sanitize_text("Line1\r\nLine2\rLine3")
        assert "\r" not in result
        assert result.count("\n") == 2

    def test_limit_length(self):
        """Test limiting text length"""
        content = "A" * 20000
        result = sanitize_text(content, max_length=10000)
        assert len(result) <= 10000
