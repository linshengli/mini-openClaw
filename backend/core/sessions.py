from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.messages import messages_from_dict, messages_to_dict
from core.paths import SESSIONS_DIR


SAFE_SESSION_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")


def _session_path(session_id: str) -> Path:
    if not SAFE_SESSION_RE.match(session_id):
        raise ValueError("Invalid session_id")
    return SESSIONS_DIR / f"{session_id}.json"


def load_session(session_id: str) -> list[dict[str, Any]]:
    path = _session_path(session_id)
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if _looks_like_langchain_messages(raw):
        return [_message_to_legacy_dict(msg) for msg in messages_from_dict(raw)]
    return raw


def save_session(session_id: str, messages: list[dict[str, Any]]) -> None:
    path = _session_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")


def load_session_messages(session_id: str) -> list[BaseMessage]:
    path = _session_path(session_id)
    if not path.exists():
        return []

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    if _looks_like_langchain_messages(raw):
        return messages_from_dict(raw)
    return [_legacy_dict_to_message(item) for item in raw if isinstance(item, dict)]


def save_session_messages(session_id: str, messages: list[Any]) -> None:
    path = _session_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _coerce_to_langchain_messages(messages)
    payload = messages_to_dict(normalized)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def list_sessions() -> list[str]:
    return sorted(file.stem for file in SESSIONS_DIR.glob("*.json"))


def _looks_like_langchain_messages(data: Any) -> bool:
    return isinstance(data, list) and bool(data) and all(
        isinstance(item, dict) and "type" in item and "data" in item for item in data
    )


def _legacy_dict_to_message(item: dict[str, Any]) -> BaseMessage:
    role = str(item.get("role", "user"))
    content = item.get("content", "")
    if role == "assistant":
        return AIMessage(content=content)
    if role == "system":
        return SystemMessage(content=content)
    if role == "tool":
        return ToolMessage(content=content, tool_call_id=str(item.get("tool_call_id", "tool_call")))
    return HumanMessage(content=content)


def _message_to_legacy_dict(message: BaseMessage) -> dict[str, Any]:
    if isinstance(message, HumanMessage):
        return {"role": "user", "content": message.content}
    if isinstance(message, AIMessage):
        payload: dict[str, Any] = {"role": "assistant", "content": message.content}
        if message.tool_calls:
            payload["tool_calls"] = message.tool_calls
        return payload
    if isinstance(message, SystemMessage):
        return {"role": "system", "content": message.content}
    if isinstance(message, ToolMessage):
        return {
            "role": "tool",
            "content": message.content,
            "tool_call_id": message.tool_call_id,
            "name": message.name,
        }
    return {"role": "assistant", "content": str(message.content)}


def _coerce_to_langchain_messages(messages: list[Any]) -> list[BaseMessage]:
    if not messages:
        return []
    if _looks_like_langchain_messages(messages):
        return messages_from_dict(messages)
    normalized: list[BaseMessage] = []
    for item in messages:
        if isinstance(item, BaseMessage):
            normalized.append(item)
        elif isinstance(item, dict):
            normalized.append(_legacy_dict_to_message(item))
    return normalized
