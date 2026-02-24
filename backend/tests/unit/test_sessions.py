from __future__ import annotations

import pytest

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
