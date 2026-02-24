from __future__ import annotations

import pytest

from core import agent_runtime, sessions


class _FailAgent:
    def invoke(self, payload):  # noqa: D401
        raise RuntimeError("model failed")


class _OkAgent:
    def invoke(self, payload):  # noqa: D401
        return {"messages": [{"role": "assistant", "content": "done"}]}


def test_runtime_uses_fallback_and_persists_session(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sessions, "SESSIONS_DIR", tmp_path / "sessions")
    monkeypatch.setattr(agent_runtime, "refresh_skills_snapshot", lambda: "<available_skills></available_skills>")
    monkeypatch.setattr(agent_runtime, "build_system_prompt", lambda: "system")

    calls: list[str] = []

    def fake_create_agent(*, model, tools, system_prompt):
        calls.append(model)
        return _FailAgent() if model == "m1" else _OkAgent()

    monkeypatch.setattr(agent_runtime, "create_agent", fake_create_agent)
    runtime = agent_runtime.MiniOpenClawRuntime(model="m1", fallback_models=["m2"], project_root=tmp_path)

    out = runtime.chat_once("s1", "hello")
    assert out == "done"
    assert calls == ["m1", "m2"]

    saved = sessions.load_session("s1")
    assert saved[-2] == {"role": "user", "content": "hello"}
    assert saved[-1] == {"role": "assistant", "content": "done"}


def test_runtime_raises_when_all_models_fail(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(agent_runtime, "refresh_skills_snapshot", lambda: "<available_skills></available_skills>")
    monkeypatch.setattr(agent_runtime, "build_system_prompt", lambda: "system")
    monkeypatch.setattr(agent_runtime, "create_agent", lambda **kwargs: _FailAgent())

    runtime = agent_runtime.MiniOpenClawRuntime(model="m1", fallback_models=["m2"], project_root=tmp_path)
    with pytest.raises(RuntimeError, match="all models failed"):
        runtime.chat_once("s2", "hello")
