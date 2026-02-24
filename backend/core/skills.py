from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from core.paths import SKILLS_DIR, SKILLS_SNAPSHOT_FILE


@dataclass
class SkillMeta:
    name: str
    description: str
    location: str


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", flags=re.DOTALL)


def _parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    lines = match.group(1).splitlines()
    parsed: dict[str, str] = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def scan_skills() -> list[SkillMeta]:
    items: list[SkillMeta] = []
    for skill_file in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        text = skill_file.read_text(encoding="utf-8")
        meta = _parse_frontmatter(text)
        name = meta.get("name") or skill_file.parent.name
        description = meta.get("description") or "No description"
        rel_path = f"./backend/{skill_file.relative_to(SKILLS_DIR.parent).as_posix()}"
        items.append(SkillMeta(name=name, description=description, location=rel_path))
    return items


def build_skills_snapshot(skills: list[SkillMeta]) -> str:
    lines = ["<available_skills>"]
    for skill in skills:
        lines.extend(
            [
                "  <skill>",
                f"    <name>{skill.name}</name>",
                f"    <description>{skill.description}</description>",
                f"    <location>{skill.location}</location>",
                "  </skill>",
            ]
        )
    lines.append("</available_skills>")
    return "\n".join(lines) + "\n"


def refresh_skills_snapshot() -> str:
    skills = scan_skills()
    snapshot = build_skills_snapshot(skills)
    SKILLS_SNAPSHOT_FILE.write_text(snapshot, encoding="utf-8")
    return snapshot

