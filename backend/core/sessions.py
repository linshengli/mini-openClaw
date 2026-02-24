from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

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
    return json.loads(path.read_text(encoding="utf-8"))


def save_session(session_id: str, messages: list[dict[str, Any]]) -> None:
    path = _session_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")


def list_sessions() -> list[str]:
    return sorted(file.stem for file in SESSIONS_DIR.glob("*.json"))

