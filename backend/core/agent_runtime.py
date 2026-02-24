from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage

from core.bootstrap import ensure_scaffold
from core.prompt import build_system_prompt
from core.sessions import load_session_messages, save_session_messages
from core.skills import refresh_skills_snapshot
from tools.core_tools import build_core_tools


def _extract_text(agent_output: Any) -> str:
    if isinstance(agent_output, str):
        return agent_output
    if isinstance(agent_output, dict):
        messages = agent_output.get("messages")
        if isinstance(messages, list) and messages:
            last = messages[-1]
            if isinstance(last, dict):
                content = last.get("content")
                if isinstance(content, str):
                    return content
            content = getattr(last, "content", None)
            if isinstance(content, str):
                return content
        for key in ("output", "result", "final_output"):
            value = agent_output.get(key)
            if isinstance(value, str):
                return value
    return str(agent_output)


class MiniOpenClawRuntime:
    def __init__(self, model: str, project_root, fallback_models: list[str] | None = None) -> None:
        ensure_scaffold()
        self.model = model
        self.fallback_models = fallback_models or []
        self.project_root = project_root
        self.tools = build_core_tools(project_root)

    def _build_agent(self, model_name: str):
        refresh_skills_snapshot()
        system_prompt = build_system_prompt()
        return create_agent(model=model_name, tools=self.tools, system_prompt=system_prompt)

    def chat_once(self, session_id: str, message: str) -> str:
        history = load_session_messages(session_id)
        input_messages = history + [HumanMessage(content=message)]

        models = [self.model] + [m for m in self.fallback_models if m and m != self.model]
        last_error: Exception | None = None
        assistant_text = ""
        messages_for_save: list[Any] = []
        for model_name in models:
            try:
                agent = self._build_agent(model_name)
                result = agent.invoke({"messages": input_messages})
                assistant_text = _extract_text(result)
                if isinstance(result, dict) and isinstance(result.get("messages"), list):
                    result_messages = result["messages"]
                    messages_for_save = (
                        input_messages + result_messages
                        if len(result_messages) <= len(input_messages)
                        else result_messages
                    )
                else:
                    messages_for_save = input_messages + [AIMessage(content=assistant_text)]
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue

        if not assistant_text and last_error is not None:
            raise RuntimeError(
                f"all models failed: {models}. last_error={last_error}"
            ) from last_error

        save_session_messages(session_id, messages_for_save)
        return assistant_text
