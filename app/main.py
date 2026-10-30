"""VowBridge AI Pro — agentic cultural wedding planner."""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from app.planner import PlanError, build_plan
from app.qloo import FixtureQlooClient, QlooClient, QlooError

load_dotenv()
app = FastAPI(title="VowBridge AI Pro", version="1.0.0", docs_url=None, redoc_url=None)
qloo = QlooClient()
fixture = FixtureQlooClient()
BASE = Path(__file__).resolve().parent
_requests = defaultdict(deque)


class PlanRequest(BaseModel):
    group_a: list[str] = Field(min_length=1, max_length=4)
    group_b: list[str] = Field(min_length=1, max_length=4)
    duration: int = Field(default=180, ge=60, le=240, multiple_of=10)
    banned: list[str] = Field(default_factory=list, max_length=20)
    vibe: str = Field(default="balanced", pattern="^(balanced|elegant|high-energy)$")
    preview: bool = False

    @field_validator('group_a', 'group_b', 'banned')
    @classmethod
    def validate_names(cls, names: list[str]) -> list[str]:
        if any(not name.strip() or len(name) > 65 for name in names):
            raise ValueError("Artist names must be 1–65 characters")
        return [name.strip() for name in names]


@app.get("/")
def home():
    return FileResponse(BASE / "index.html")


@app.get("/assets/styles.css")
def css():
    return FileResponse(BASE / "styles.css", media_type="text/css")


@app.get("/assets/app.js")
def js():
    return FileResponse(BASE / "app.js", media_type="application/javascript")


@app.get("/api/health")
def health():
    return {"ok": True, "service": "VowBridge AI Pro", "live_qloo_available": qloo.configured}


@app.post("/api/plan")
async def plan(request: Request, payload: PlanRequest):
    # Per-instance IP throttling protects the shared hackathon key from unbounded API usage.
    identity = request.client.host if request.client else "unknown"
    now = time.monotonic()
    recent = _requests[identity]
    while recent and now - recent[0] > 300:
        recent.popleft()
    limit = 24 if payload.preview else 8
    if len(recent) >= limit:
        raise HTTPException(429, "Demo rate limit reached. Please retry in a few minutes.")
    recent.append(now)
    if not payload.preview and not qloo.configured:
        raise HTTPException(503, "Live Qloo mode requires QLOO_API_KEY on the server. Use synthetic preview only for UI testing.")
    try:
        result = await build_plan(fixture if payload.preview else qloo, payload.group_a, payload.group_b,
                                  payload.duration, payload.banned, payload.vibe, preview=payload.preview)
        return result
    except PlanError as exc:
        raise HTTPException(422, str(exc)) from exc
    except QlooError as exc:
        raise HTTPException(502, str(exc)) from exc
