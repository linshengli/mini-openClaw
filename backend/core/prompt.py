from __future__ import annotations

from pathlib import Path

from core.paths import MEMORY_FILE, WORKSPACE_DIR


MAX_FILE_CHARS = 20_000


def _read_truncated(path: Path) -> str:
    if not path.exists():
        return f"[missing] {path.name}\n"
    content = path.read_text(encoding="utf-8")
    if len(content) <= MAX_FILE_CHARS:
        return content
    return content[:MAX_FILE_CHARS] + "\n...[truncated]\n"


def build_system_prompt() -> str:
    parts: list[str] = []
    ordered_files = [
        WORKSPACE_DIR / "SKILLS_SNAPSHOT.md",
        WORKSPACE_DIR / "SOUL.md",
        WORKSPACE_DIR / "IDENTITY.md",
        WORKSPACE_DIR / "USER.md",
        WORKSPACE_DIR / "AGENTS.md",
        MEMORY_FILE,
    ]
    for file_path in ordered_files:
        parts.append(f"\n\n<!-- {file_path.name} -->\n")
        parts.append(_read_truncated(file_path))
    return "".join(parts).strip()

