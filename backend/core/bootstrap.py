from __future__ import annotations

from pathlib import Path

from core.paths import MEMORY_DIR, MEMORY_FILE, SESSIONS_DIR, SKILLS_DIR, STORAGE_DIR, WORKSPACE_DIR


DEFAULT_FILES: dict[Path, str] = {
    WORKSPACE_DIR / "SOUL.md": "# SOUL\n\n你是 mini OpenClaw，一个透明、可靠、可追踪的本地智能助手。\n",
    WORKSPACE_DIR / "IDENTITY.md": "# IDENTITY\n\n你通过文件系统管理记忆与技能，优先可解释性。\n",
    WORKSPACE_DIR / "USER.md": "# USER\n\n用户偏好：工程化、可落地、可验证。\n",
    WORKSPACE_DIR
    / "AGENTS.md": """# 操作指南

## 技能调用协议 (SKILL PROTOCOL)
你拥有一个技能列表 (SKILLS_SNAPSHOT)，其中列出了你可以使用的能力及其定义文件的位置。
当你要使用某个技能时，必须严格遵守以下步骤：
1. 第一步永远是使用 `read_file` 工具读取对应的 `location` 路径下的 Markdown 文件。
2. 仔细阅读文件中的内容、步骤和示例。
3. 根据文件中的指示，结合你内置的 Core Tools (terminal, python_repl, fetch_url) 执行任务。
禁止直接猜测技能用法，必须先读取文件。

## 记忆协议
1. 先检索已有记忆，避免重复写入。
2. 只记录长期有价值信息到 MEMORY.md。
3. 对不确定信息明确标注不确定。
""",
    MEMORY_FILE: "# MEMORY\n\n- 初始记忆为空。\n",
    SKILLS_DIR
    / "get_weather"
    / "SKILL.md": """---
name: get_weather
description: 获取指定城市天气（演示技能）
---

# get_weather

1. 使用 `fetch_url` 获取天气 API 或网页。
2. 必要时用 `python_repl` 清洗结构化数据。
3. 输出城市、温度、天气概况、数据来源与时间。
""",
}


def ensure_scaffold() -> None:
    for path in [MEMORY_DIR, SESSIONS_DIR, SKILLS_DIR, WORKSPACE_DIR, STORAGE_DIR]:
        path.mkdir(parents=True, exist_ok=True)

    for file_path, content in DEFAULT_FILES.items():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if not file_path.exists():
            file_path.write_text(content, encoding="utf-8")

