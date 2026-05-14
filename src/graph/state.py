"""LangGraph state schema for the research workflow.

We keep the state typed end-to-end. Parallel-write fields use reducers so
concurrent nodes append instead of overwriting each other.
"""
from __future__ import annotations

from operator import add
from typing import Annotated, Any, TypedDict


class ResearchState(TypedDict, total=False):
    # Inputs
    question: str

    # Planner output
    sub_questions: list[str]

    # Retrieval / research outputs (parallel writers — must be reducer-enabled)
    chunks: Annotated[list[dict[str, Any]], add]

    # Synthesis
    draft: str
    fact_check: dict[str, Any]
    iterations: int

    # Final
    final_report: str
