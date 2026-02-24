from __future__ import annotations

from fastapi.testclient import TestClient

import app as app_module


def test_chat_non_stream(monkeypatch) -> None:
    monkeypatch.setattr(app_module.runtime, "chat_once", lambda session_id, message: "pong")
    client = TestClient(app_module.app)

    resp = client.post("/api/chat", json={"message": "ping", "stream": False, "session_id": "s1"})
    assert resp.status_code == 200
    assert resp.json() == {"reply": "pong"}


def test_chat_rejects_invalid_session_id() -> None:
    client = TestClient(app_module.app)

    resp = client.post("/api/chat", json={"message": "ping", "stream": False, "session_id": "../bad"})
    assert resp.status_code == 422


def test_stream_chat_sse(monkeypatch) -> None:
    monkeypatch.setattr(app_module.runtime, "chat_once", lambda session_id, message: "ok")
    client = TestClient(app_module.app)

    resp = client.post("/api/chat", json={"message": "hello", "stream": True, "session_id": "s2"})
    assert resp.status_code == 200
    assert '"type": "status"' in resp.text
    assert '"type": "final"' in resp.text


def test_files_api_write_and_read() -> None:
    client = TestClient(app_module.app)
    path = "backend/workspace/_tmp_test_file.txt"

    write_resp = client.post("/api/files", json={"path": path, "content": "abc"})
    assert write_resp.status_code == 200

    read_resp = client.get("/api/files", params={"path": path})
    assert read_resp.status_code == 200
    assert read_resp.json()["content"] == "abc"


def test_files_api_block_path_escape() -> None:
    client = TestClient(app_module.app)

    resp = client.get("/api/files", params={"path": "../../etc/passwd"})
    assert resp.status_code == 400
