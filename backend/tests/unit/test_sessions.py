from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from core import sessions


def test_session_path_rejects_invalid_id() -> None:
    with pytest.raises(ValueError):
        sessions._session_path("../bad")


def test_save_and_load_session_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sessions, "SESSIONS_DIR", tmp_path)
    payload = [{"role": "user", "content": "hello"}]
    sessions.save_session("abc_1", payload)

    assert sessions.load_session("abc_1") == payload


def test_list_sessions_sorted(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sessions, "SESSIONS_DIR", tmp_path)
    sessions.save_session("zeta", [])
    sessions.save_session("alpha", [])

    assert sessions.list_sessions() == ["alpha", "zeta"]


def test_save_session_messages_roundtrip_with_tool(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sessions, "SESSIONS_DIR", tmp_path)
    payload = [
        HumanMessage(content="ping"),
        AIMessage(content="", tool_calls=[{"name": "terminal", "args": {"command": "echo hi"}, "id": "call_1", "type": "tool_call"}]),
        ToolMessage(content="hi", tool_call_id="call_1", name="terminal"),
        AIMessage(content="pong"),
    ]
    sessions.save_session_messages("m1", payload)

    loaded_messages = sessions.load_session_messages("m1")
    assert len(loaded_messages) == 4

    loaded_legacy = sessions.load_session("m1")
    assert loaded_legacy[0]["role"] == "user"
    assert loaded_legacy[-1]["content"] == "pong"
