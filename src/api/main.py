"""FastAPI service wrapping the LangGraph research workflow.

POST /research   — SSE stream of node updates, ending with the final report.
GET  /health     — liveness + dependency check.

Run:
    uvicorn src.api.main:app --reload --port 8000
"""
from __future__ import annotations

import json
import logging
import os
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.config import MAIN_MODEL
from src.graph.workflow import get_app
from src.logging_setup import configure_logging
from src.rag.db import ping as pg_ping

configure_logging()
log = logging.getLogger(__name__)

app = FastAPI(title="Deep Research Agent", version="1.0.0")

_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ---------- Schemas --------------------------------------------------------

class ResearchRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    thread_id: str | None = Field(default=None, max_length=128)


# ---------- SSE helpers ----------------------------------------------------

def _sse(event: str, data: dict | str) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


async def _stream_research(question: str, thread_id: str) -> AsyncIterator[str]:
    graph = get_app()
    config = {"configurable": {"thread_id": thread_id}}
    final_report: str = ""

    yield _sse("start", {"question": question, "thread_id": thread_id})

    try:
        async for event in graph.astream(
            {"question": question, "iterations": 0},
            config=config,
            stream_mode="updates",
        ):
            for node, update in event.items():
                # Don't dump the whole chunk list to the client every tick — too noisy.
                summary = _summarize_update(update)
                yield _sse("node", {"node": node, "update": summary})
                if isinstance(update, dict) and update.get("final_report"):
                    final_report = update["final_report"]
    except Exception as e:
        log.exception("workflow failed")
        yield _sse("error", {"message": str(e)})
        return

    yield _sse("final", {"report": final_report})
    yield _sse("done", "ok")


def _summarize_update(update: object) -> dict:
    if not isinstance(update, dict):
        return {"raw": str(update)}
    out: dict = {}
    for k, v in update.items():
        if k == "chunks" and isinstance(v, list):
            out["chunks_added"] = len(v)
        elif k == "draft" and isinstance(v, str):
            out["draft_preview"] = v[:240]
        elif k == "final_report" and isinstance(v, str):
            out["final_report_chars"] = len(v)
        else:
            out[k] = v
    return out


# ---------- Routes ---------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model": MAIN_MODEL,
        "pgvector": pg_ping(),
    }


@app.post("/research")
async def research(req: ResearchRequest) -> StreamingResponse:
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question is empty")
    thread_id = req.thread_id or "anon"
    log.info("research request: thread=%s q=%r", thread_id, req.question)
    return StreamingResponse(
        _stream_research(req.question, thread_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
