"""FastAPI server — OpenEnv HTTP API for SupportDeskEnv."""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from environment import SupportDeskEnv, VALID_TASKS
from models import Action

app = FastAPI(
    title="SupportDeskEnv",
    description="Customer support ticket triage and response environment for AI agents.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# One env per session; for simplicity we keep a single default session.
_sessions: Dict[str, SupportDeskEnv] = {}


# ── Request/Response schemas ───────────────────────────────────────────────

class ResetRequest(BaseModel):
    task: Optional[str] = "ticket-classify"
    session_id: Optional[str] = "default"


class StepRequest(BaseModel):
    action: Dict[str, Any]
    session_id: Optional[str] = "default"


class StateRequest(BaseModel):
    session_id: Optional[str] = "default"


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/")
async def root() -> Dict[str, Any]:
    return {
        "name": "SupportDeskEnv",
        "version": "1.0.0",
        "description": "Customer support ticket triage and response environment",
        "tasks": VALID_TASKS,
        "endpoints": ["/reset", "/step", "/state", "/health"],
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/reset")
async def reset(request: ResetRequest = ResetRequest()) -> Dict[str, Any]:
    task = request.task or "ticket-classify"
    if task not in VALID_TASKS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid task {task!r}. Must be one of {VALID_TASKS}",
        )
    sid = request.session_id or "default"
    env = SupportDeskEnv(task=task)
    _sessions[sid] = env
    result = env.reset()
    return result.model_dump()


@app.post("/step")
async def step(request: StepRequest) -> Dict[str, Any]:
    sid = request.session_id or "default"
    env = _sessions.get(sid)
    if env is None:
        raise HTTPException(status_code=400, detail="No active session. Call /reset first.")
    try:
        action = Action(**request.action)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid action: {exc}")
    result = env.step(action)
    return result.model_dump()


@app.get("/state")
async def state(session_id: str = "default") -> Dict[str, Any]:
    env = _sessions.get(session_id)
    if env is None:
        raise HTTPException(status_code=400, detail="No active session. Call /reset first.")
    return env.state().model_dump()


@app.post("/state")
async def state_post(request: StateRequest = StateRequest()) -> Dict[str, Any]:
    sid = request.session_id or "default"
    env = _sessions.get(sid)
    if env is None:
        raise HTTPException(status_code=400, detail="No active session. Call /reset first.")
    return env.state().model_dump()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
