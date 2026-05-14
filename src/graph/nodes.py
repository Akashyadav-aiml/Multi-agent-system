"""Node implementations for the research graph.

Each node is a pure function of state → partial state update. LLM calls use
the langchain wrapper from `src.config.make_langchain_llm` so we can swap
providers (Gemini, Ollama, Anthropic) without touching this file.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, ValidationError

from src.config import make_langchain_llm
from src.rag.retriever import Hit, vector_search
from src.tools.arxiv_search import ArxivSearchTool

log = logging.getLogger(__name__)

MAX_ITERATIONS = 3


# ---------- Structured-output schemas -------------------------------------

class PlanOutput(BaseModel):
    sub_questions: list[str] = Field(..., min_length=1, max_length=8)


class FactCheckOutput(BaseModel):
    grounded: bool = Field(..., description="Are the draft's main claims supported by the chunks?")
    rationale: str = Field(..., description="One sentence per problem; empty if grounded.")


# ---------- Helpers --------------------------------------------------------

def _hit_to_chunk_dict(h: Hit, source: str) -> dict[str, Any]:
    return {
        "arxiv_id": h.arxiv_id,
        "chunk_index": h.chunk_index,
        "content": h.content,
        "score": h.score,
        "title": h.title,
        "published": h.published,
        "source": source,
    }


def _parse_json_strict(model: type[BaseModel], raw: str) -> BaseModel | None:
    """LLMs sometimes wrap JSON in ```json fences or trailing prose. Strip and parse."""
    candidate = raw.strip()
    m = re.search(r"\{.*\}", candidate, flags=re.DOTALL)
    if m:
        candidate = m.group(0)
    try:
        return model.model_validate_json(candidate)
    except ValidationError as e:
        log.warning("Could not parse %s output: %s", model.__name__, e)
        return None


# ---------- Nodes ----------------------------------------------------------

def plan_node(state: dict) -> dict:
    llm = make_langchain_llm("router")  # cheap model — decomposition is easy
    prompt = [
        SystemMessage(content=(
            "You decompose research questions into 3-5 specific, searchable sub-questions. "
            "Respond ONLY with JSON of shape {\"sub_questions\": [\"...\", \"...\"]}."
        )),
        HumanMessage(content=state["question"]),
    ]
    resp = llm.invoke(prompt)
    parsed = _parse_json_strict(PlanOutput, resp.content)
    if parsed is None:
        # Fallback: treat the question as a single sub-question rather than crash.
        return {"sub_questions": [state["question"]], "iterations": 0}
    log.info("plan_node → %d sub-questions", len(parsed.sub_questions))
    return {"sub_questions": parsed.sub_questions, "iterations": 0}


def retrieve_node(state: dict) -> dict:
    sub_qs = state.get("sub_questions") or [state["question"]]
    all_hits: list[dict] = []
    for sq in sub_qs:
        hits = vector_search(sq, top_k=4)
        all_hits.extend(_hit_to_chunk_dict(h, source="rag") for h in hits)
    log.info("retrieve_node → %d chunks from local corpus", len(all_hits))
    return {"chunks": all_hits}


def research_node(state: dict) -> dict:
    """Pull fresh evidence from arXiv for each sub-question."""
    tool = ArxivSearchTool()
    sub_qs = state.get("sub_questions") or [state["question"]]
    new_chunks: list[dict] = []
    for sq in sub_qs:
        raw = tool._run(query=sq, max_results=3)
        # arxiv_search returns a single formatted blob. We store it as one
        # synthetic "chunk" per sub-question — good enough for downstream
        # grounding without re-parsing.
        new_chunks.append({
            "arxiv_id": "live",
            "chunk_index": 0,
            "content": raw,
            "score": None,
            "title": f"arxiv_search: {sq}",
            "published": None,
            "source": "arxiv",
        })
    log.info("research_node → %d arxiv blobs", len(new_chunks))
    return {"chunks": new_chunks}


def _chunks_for_prompt(chunks: list[dict], max_chars: int = 8000) -> str:
    parts: list[str] = []
    used = 0
    for c in chunks:
        head = f"[{c.get('source','?')} :: arXiv:{c.get('arxiv_id','?')}#{c.get('chunk_index',0)}]"
        body = c.get("content", "").strip()
        block = f"{head}\n{body}"
        if used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block)
    return "\n\n".join(parts) if parts else "(no evidence)"


def write_node(state: dict) -> dict:
    llm = make_langchain_llm("main")
    evidence = _chunks_for_prompt(state.get("chunks", []))
    prompt = [
        SystemMessage(content=(
            "You are a senior technical writer. Write a research report answering the user's "
            "question using ONLY the provided evidence. Cite inline as [arXiv:ID]. "
            "If the evidence is thin, say so explicitly. Markdown."
        )),
        HumanMessage(content=(
            f"Question: {state['question']}\n\n"
            f"Sub-questions:\n- " + "\n- ".join(state.get("sub_questions") or [state["question"]]) +
            f"\n\nEvidence:\n{evidence}\n\n"
            "Output a complete markdown report with sections: Direct Answer, Findings, "
            "Open Questions, References."
        )),
    ]
    resp = llm.invoke(prompt)
    return {"draft": resp.content}


def fact_check_node(state: dict) -> dict:
    llm = make_langchain_llm("router")  # binary judgment — small model OK
    evidence = _chunks_for_prompt(state.get("chunks", []), max_chars=6000)
    prompt = [
        SystemMessage(content=(
            "You are a strict fact-checker. Given a draft and the evidence chunks it should "
            "be grounded in, answer whether the draft's MAIN claims are supported. Ignore minor "
            "phrasing issues. Respond ONLY with JSON: "
            "{\"grounded\": true|false, \"rationale\": \"one sentence per problem; empty if grounded\"}."
        )),
        HumanMessage(content=(
            f"Draft:\n{state.get('draft','')}\n\n"
            f"Evidence:\n{evidence}"
        )),
    ]
    resp = llm.invoke(prompt)
    parsed = _parse_json_strict(FactCheckOutput, resp.content)
    if parsed is None:
        # Fail open — don't loop forever just because the judge couldn't be parsed.
        result = {"grounded": True, "rationale": "fact-check parse failed; assuming grounded"}
    else:
        result = parsed.model_dump()
    iterations = int(state.get("iterations", 0)) + 1
    log.info("fact_check_node → grounded=%s (iter=%d)", result["grounded"], iterations)
    return {"fact_check": result, "iterations": iterations}


def edit_node(state: dict) -> dict:
    llm = make_langchain_llm("main")
    prompt = [
        SystemMessage(content=(
            "You are an editor. Polish the draft for clarity and concision. Preserve every "
            "citation. Output the polished markdown only — no preamble."
        )),
        HumanMessage(content=state.get("draft", "")),
    ]
    resp = llm.invoke(prompt)
    return {"final_report": resp.content}


# ---------- Conditional edge ----------------------------------------------

def should_retry(state: dict) -> str:
    fc = state.get("fact_check") or {}
    if fc.get("grounded"):
        return "write"
    if int(state.get("iterations", 0)) >= MAX_ITERATIONS:
        return "write"
    return "research"
