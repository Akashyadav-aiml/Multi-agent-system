"""Streamlit UI for the Deep Research Agent.

Talks to the FastAPI service at $BACKEND_URL (default: http://localhost:8000).
Renders SSE node updates as a live timeline; final report renders as markdown.

Run:
    streamlit run frontend/app.py
"""
from __future__ import annotations

import json
import os
import time
from typing import Iterator

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
REQUEST_TIMEOUT = int(os.getenv("FRONTEND_TIMEOUT", "300"))


# ---------- SSE helpers ----------------------------------------------------

def _parse_sse_stream(resp: requests.Response) -> Iterator[tuple[str, str]]:
    """Yield (event_name, raw_data) pairs from an SSE response."""
    event_name = "message"
    data_lines: list[str] = []
    for raw in resp.iter_lines(decode_unicode=True):
        if raw is None:
            continue
        if raw == "":
            if data_lines:
                yield event_name, "\n".join(data_lines)
                data_lines = []
                event_name = "message"
            continue
        if raw.startswith(":"):
            continue  # comment
        if raw.startswith("event:"):
            event_name = raw[len("event:"):].strip()
        elif raw.startswith("data:"):
            data_lines.append(raw[len("data:"):].lstrip())


def _safe_json(s: str) -> dict | str:
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return s


# ---------- UI -------------------------------------------------------------

st.set_page_config(page_title="Deep Research Agent", page_icon="🔬", layout="wide")

_title_col, _mode_col = st.columns([3, 1])
with _title_col:
    st.title("🔬 Deep Research Agent")
    st.caption("CrewAI + LangGraph + pgvector + Gemini — answers arXiv research questions with cited sources.")
with _mode_col:
    st.write("")  # vertical spacer to align with title baseline
    try:
        mode = st.segmented_control(
            "Mode",
            options=["online", "offline"],
            format_func=lambda m: "🌐 Online" if m == "online" else "💾 Offline",
            default="online",
            label_visibility="collapsed",
        )
    except AttributeError:
        # Older Streamlit (< 1.40): fall back to horizontal radio.
        mode = st.radio(
            "Mode",
            options=["online", "offline"],
            format_func=lambda m: "🌐 Online" if m == "online" else "💾 Offline",
            index=0,
            horizontal=True,
            label_visibility="collapsed",
        )
    if mode is None:
        mode = "online"

# Health badge
try:
    h = requests.get(f"{BACKEND_URL}/health", timeout=5).json()
    badge = "🟢" if h.get("status") == "ok" else "🔴"
    pg = "✅" if h.get("pgvector") else "⚠️"
    st.caption(f"{badge} backend `{BACKEND_URL}` · model `{h.get('model','?')}` · pgvector {pg} · mode `{mode}`")
except Exception as e:
    st.caption(f"🔴 backend unreachable at `{BACKEND_URL}` ({e})")

question = st.text_area(
    "Research question",
    placeholder="e.g. What are the most effective reranking strategies for RAG in 2025?",
    height=80,
)
go = st.button("Research", type="primary", disabled=not question.strip())

if go:
    col_progress, col_report = st.columns([1, 2])

    with col_progress:
        st.subheader("Pipeline")
        progress_box = st.empty()
        events_log: list[str] = []

    with col_report:
        st.subheader("Report")
        report_box = st.empty()
        report_box.info("Streaming…")

    started_at = time.time()
    try:
        with requests.post(
            f"{BACKEND_URL}/research",
            json={"question": question, "thread_id": f"st-{int(started_at)}", "mode": mode},
            stream=True,
            timeout=REQUEST_TIMEOUT,
            headers={"Accept": "text/event-stream"},
        ) as r:
            if r.status_code != 200:
                report_box.error(f"backend returned {r.status_code}: {r.text}")
                st.stop()

            final_report = ""
            for event, data in _parse_sse_stream(r):
                payload = _safe_json(data)
                if event == "start":
                    events_log.append("▸ workflow started")
                elif event == "node":
                    if isinstance(payload, dict):
                        node = payload.get("node", "?")
                        upd = payload.get("update", {})
                        summary = ", ".join(f"{k}={v}" for k, v in (upd.items() if isinstance(upd, dict) else []))
                        events_log.append(f"• **{node}** — {summary or '…'}")
                    else:
                        events_log.append(f"• node event: {payload}")
                elif event == "final":
                    final_report = payload.get("report", "") if isinstance(payload, dict) else str(payload)
                    events_log.append("✓ final report generated")
                elif event == "error":
                    msg = payload.get("message", payload) if isinstance(payload, dict) else payload
                    events_log.append(f"✗ error: {msg}")
                    report_box.error(f"backend error: {msg}")
                elif event == "done":
                    events_log.append(f"✓ done in {time.time() - started_at:.1f}s")

                progress_box.markdown("\n\n".join(events_log))

            if final_report:
                report_box.markdown(final_report)
            elif not events_log or "error" not in events_log[-1]:
                report_box.warning("Stream ended without a final report.")
    except requests.RequestException as e:
        report_box.error(f"request failed: {e}")

st.divider()
with st.expander("How this works"):
    st.markdown(
        "1. **Plan** — router LLM decomposes the question into sub-questions.\n"
        "2. **Retrieve + Research** (parallel) — vector search over local arXiv corpus and live arXiv API.\n"
        "3. **Fact-check** — judges whether the draft's claims are grounded; loops back if not (cap=3).\n"
        "4. **Write + Edit** — synthesize and polish the final report.\n\n"
        f"Backend: `{BACKEND_URL}` · set `BACKEND_URL` env var to point elsewhere."
    )
