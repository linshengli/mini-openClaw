from __future__ import annotations

from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
MEMORY_DIR = BACKEND_DIR / "memory"
SESSIONS_DIR = BACKEND_DIR / "sessions"
SKILLS_DIR = BACKEND_DIR / "skills"
WORKSPACE_DIR = BACKEND_DIR / "workspace"
KNOWLEDGE_DIR = BACKEND_DIR / "knowledge"
STORAGE_DIR = BACKEND_DIR / "storage"
SKILLS_SNAPSHOT_FILE = WORKSPACE_DIR / "SKILLS_SNAPSHOT.md"
MEMORY_FILE = MEMORY_DIR / "MEMORY.md"

