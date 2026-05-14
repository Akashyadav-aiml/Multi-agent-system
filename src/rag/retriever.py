"""Vector retrieval over pgvector.

Exposes two surfaces:
  1. vector_search(...)   — plain Python function used by LangGraph nodes.
  2. VectorSearchTool     — CrewAI tool wrapping it for Week 3 agents.

Uses cosine distance via pgvector's `<=>` operator. Similarity = 1 - distance.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Type

from crewai.tools import BaseTool
from pgvector.psycopg import Vector
from pydantic import BaseModel, Field

from src.config import get_embeddings
from src.rag.db import connect

log = logging.getLogger(__name__)


@dataclass(slots=True)
class Hit:
    arxiv_id: str
    chunk_index: int
    content: str
    score: float          # 0..1, higher = more similar
    title: str | None
    published: str | None
    metadata: dict[str, Any]


def vector_search(
    query: str,
    *,
    top_k: int = 5,
    min_score: float = 0.0,
    published_after: str | None = None,
    rerank: bool = True,
    oversample: int = 4,
) -> list[Hit]:
    """Embed `query`, return top-k chunks ordered by relevance.

    When `rerank=True` and a Cohere key is configured, we pull `top_k * oversample`
    candidates from pgvector (capped at 20) and rerank them with a cross-encoder
    for better precision. Without a key we degrade to pure vector order.
    """
    if not query or not query.strip():
        return []

    fetch_n = min(20, top_k * oversample) if rerank else top_k

    emb = get_embeddings().embed_query(query)
    qvec = Vector(emb)

    sql = [
        "SELECT c.arxiv_id, c.chunk_index, c.content,",
        "       1 - (c.embedding <=> %s) AS score,",
        "       p.title, p.published_at, c.metadata",
        "  FROM chunks c",
        "  LEFT JOIN papers p ON p.arxiv_id = c.arxiv_id",
        " WHERE c.embedding IS NOT NULL",
    ]
    params: list[Any] = [qvec]

    if published_after:
        sql.append("   AND p.published_at >= %s")
        params.append(published_after)

    sql.append(" ORDER BY c.embedding <=> %s")
    sql.append(" LIMIT %s")
    params.extend([qvec, fetch_n])

    with connect() as conn, conn.cursor() as cur:
        cur.execute("\n".join(sql), params)
        rows = cur.fetchall()

    hits: list[Hit] = []
    for arxiv_id, idx, content, score, title, published, meta in rows:
        if score < min_score:
            continue
        hits.append(
            Hit(
                arxiv_id=arxiv_id,
                chunk_index=idx,
                content=content,
                score=float(score),
                title=title,
                published=published.date().isoformat() if published else None,
                metadata=meta or {},
            )
        )
    log.debug("vector_search(%r) → %d candidates", query, len(hits))

    if rerank and hits:
        # Local import to avoid a hard dep when callers explicitly disable rerank.
        from src.rag.rerank import rerank as _rerank

        hits = _rerank(query, hits, top_n=top_k)
    else:
        hits = hits[:top_k]
    return hits


def format_hits_for_llm(hits: list[Hit]) -> str:
    if not hits:
        return "No relevant chunks found in the local corpus."
    lines = [f"Retrieved {len(hits)} chunks (score=cosine similarity):\n"]
    for i, h in enumerate(hits, 1):
        head = f"[{i}] arXiv:{h.arxiv_id} (chunk {h.chunk_index}, score={h.score:.3f})"
        if h.title:
            head += f"\n    Title: {h.title}"
        if h.published:
            head += f"\n    Published: {h.published}"
        lines.append(f"{head}\n    {h.content.strip()}\n")
    return "\n".join(lines)


# ---------- CrewAI tool wrapper -------------------------------------------

class VectorSearchInput(BaseModel):
    query: str = Field(..., description="Natural-language question or topic to search the local arXiv corpus for.")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to return.")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Drop hits below this cosine similarity.")


class VectorSearchTool(BaseTool):
    name: str = "vector_search"
    description: str = (
        "Search the LOCAL arXiv corpus (pre-ingested papers stored in pgvector) "
        "for chunks most semantically similar to your query. Use this BEFORE "
        "arxiv_search when the question is likely answerable from already-ingested "
        "papers — it is faster and grounded in vetted sources. Returns chunks with "
        "arXiv IDs and similarity scores."
    )
    args_schema: Type[BaseModel] = VectorSearchInput

    def _run(self, query: str, top_k: int = 5, min_score: float = 0.0) -> str:
        try:
            hits = vector_search(query, top_k=top_k, min_score=min_score)
        except Exception as e:
            log.exception("vector_search failed")
            return f"vector_search error: {e!s}"
        return format_hits_for_llm(hits)
