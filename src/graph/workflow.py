"""Week 5+: stateful research graph.

Flow:

    START → plan → (retrieve || research) → fact_check
                                              │
                                              ├── grounded ─────────→ write → edit → END
                                              └── not grounded
                                                  └── iter < N → research (loop)
                                                  └── iter ≥ N → write   (ship draft)

The reducer on `chunks` is `add` so the parallel retrieve+research branches
both append to the shared list.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from src.graph.nodes import (
    edit_node,
    fact_check_node,
    plan_node,
    research_node,
    retrieve_node,
    should_retry,
    write_node,
)
from src.graph.state import ResearchState
from src.observability import langfuse_callbacks

log = logging.getLogger(__name__)


def _build_graph() -> StateGraph:
    g = StateGraph(ResearchState)
    g.add_node("plan", plan_node)
    g.add_node("retrieve", retrieve_node)
    g.add_node("research", research_node)
    g.add_node("fact_check", fact_check_node)
    g.add_node("write", write_node)
    g.add_node("edit", edit_node)

    g.add_edge(START, "plan")
    g.add_edge("plan", "retrieve")
    g.add_edge("plan", "research")
    g.add_edge("retrieve", "fact_check")
    g.add_edge("research", "fact_check")
    g.add_conditional_edges(
        "fact_check",
        should_retry,
        {"write": "write", "research": "research"},
    )
    g.add_edge("write", "edit")
    g.add_edge("edit", END)
    return g


def _maybe_checkpointer():
    """Postgres checkpointer if CHECKPOINT_DB set; otherwise None (in-memory by default)."""
    dsn = os.getenv("CHECKPOINT_DB")
    if not dsn:
        return None
    try:
        from langgraph.checkpoint.postgres import PostgresSaver

        cp = PostgresSaver.from_conn_string(dsn)
        cp.setup()
        log.info("LangGraph checkpointer: Postgres")
        return cp
    except Exception as e:
        log.warning("Failed to init Postgres checkpointer (%s) — running without.", e)
        return None


@lru_cache(maxsize=1)
def get_app():
    """Compile the graph once. Re-import is cheap; compile is not.

    Langfuse callbacks (if configured) are attached as default callbacks via
    `.with_config(...)` so every caller — `run()`, the FastAPI streamer,
    `run_week5.py`, the Ragas harness — gets traced without per-call wiring.
    """
    graph = _build_graph()
    app = graph.compile(checkpointer=_maybe_checkpointer())
    callbacks = langfuse_callbacks()
    if callbacks:
        log.info("Attaching %d Langfuse callback(s) to the graph", len(callbacks))
        app = app.with_config({"callbacks": callbacks})
    return app


def run(question: str, *, thread_id: str | None = None) -> dict[str, Any]:
    """Synchronous one-shot. For streaming, use get_app().astream(...) directly."""
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id or "adhoc"}}
    return get_app().invoke({"question": question, "iterations": 0}, config=config)
