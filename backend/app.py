from __future__ import annotations

import json
import os
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from core.agent_runtime import MiniOpenClawRuntime
from core.bootstrap import ensure_scaffold
from core.paths import BACKEND_DIR
from core.sessions import list_sessions


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=20_000)
    session_id: str = Field(default="main_session", pattern=r"^[a-zA-Z0-9_\-]+$", max_length=128)
    stream: bool = True


class FileSaveRequest(BaseModel):
    path: str
    content: str


app = FastAPI(title="mini OpenClaw backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ensure_scaffold()
# Always load backend/.env and override stale shell exports.
load_dotenv(BACKEND_DIR / ".env", override=True)
default_models = os.getenv(
    "OPENCLAW_MODELS",
    "openai:qwen-plus,openai:qwen3-coder-plus,",
)
parsed_models = [m.strip() for m in default_models.split(",") if m.strip()]
primary_model = os.getenv("OPENCLAW_MODEL", parsed_models[0] if parsed_models else "openai:qwen3-coder-plus")
fallback_models = parsed_models[1:] if len(parsed_models) > 1 else []
runtime = MiniOpenClawRuntime(
    model=primary_model,
    fallback_models=fallback_models,
    project_root=BACKEND_DIR.parent,
)
PROJECT_ROOT = BACKEND_DIR.parent.resolve()


def _resolve_safe(path: str) -> Path:
    normalized = path[2:] if path.startswith("./") else path
    candidate = (PROJECT_ROOT / normalized).resolve()
    try:
        candidate.relative_to(PROJECT_ROOT)
    except ValueError:
        raise HTTPException(status_code=400, detail="path out of workspace")
    return candidate


@app.post("/api/chat")
async def chat_api(req: ChatRequest):
    if not req.stream:
        answer = runtime.chat_once(session_id=req.session_id, message=req.message)
        return {"reply": answer}

    async def event_gen() -> AsyncGenerator[str, None]:
        yield f"data: {json.dumps({'type': 'status', 'value': 'running'}, ensure_ascii=False)}\n\n"
        try:
            answer = runtime.chat_once(session_id=req.session_id, message=req.message)
            yield f"data: {json.dumps({'type': 'final', 'value': answer}, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield f"data: {json.dumps({'type': 'error', 'value': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.get("/api/files")
async def read_file_api(path: str = Query(..., description="Relative workspace path")):
    target = _resolve_safe(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="file not found")
    if target.is_dir():
        raise HTTPException(status_code=400, detail="path is directory")
    return {"path": path, "content": target.read_text(encoding="utf-8")}


@app.post("/api/files")
async def write_file_api(req: FileSaveRequest):
    target = _resolve_safe(req.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(req.content, encoding="utf-8")
    return {"ok": True, "path": req.path}


@app.get("/api/sessions")
async def list_sessions_api():
    return {"sessions": list_sessions()}
