"""Cross-encoder reranking via Cohere Rerank.

Vector similarity is fast but imprecise — the top embedding match isn't
always the most relevant chunk. A cross-encoder reranker scores
(query, chunk) pairs jointly and is much more precise. We oversample from
pgvector then trim with the reranker.

If COHERE_API_KEY is unset (or Cohere fails), this falls back to the
embedding-similarity order so the rest of the pipeline keeps working.
"""
from __future__ import annotations

import logging
import os
from dataclasses import replace
from functools import lru_cache

from src.rag.retriever import Hit

log = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("COHERE_RERANK_MODEL", "rerank-english-v3.0")


@lru_cache(maxsize=1)
def _client():
    key = os.getenv("COHERE_API_KEY")
    if not key:
        return None
    try:
        import cohere

        return cohere.ClientV2(api_key=key)
    except ImportError:
        log.warning("cohere package not installed; reranker disabled")
        return None
    except Exception as e:
        log.warning("cohere client init failed: %s", e)
        return None


def rerank(
    query: str,
    hits: list[Hit],
    *,
    top_n: int = 5,
    model: str = DEFAULT_MODEL,
) -> list[Hit]:
    """Rerank `hits` by relevance to `query`. Returns top_n.

    Falls back to `hits[:top_n]` if Cohere is unavailable so callers can
    treat this as a pure no-op when no key is configured.
    """
    if not hits:
        return []
    client = _client()
    if client is None:
        log.debug("rerank: no Cohere client, returning vector-order hits[:%d]", top_n)
        return hits[:top_n]

    documents = [h.content for h in hits]
    try:
        response = client.rerank(
            model=model,
            query=query,
            documents=documents,
            top_n=min(top_n, len(documents)),
        )
    except Exception as e:
        log.warning("Cohere rerank failed (%s); falling back to vector order", e)
        return hits[:top_n]

    out: list[Hit] = []
    for r in response.results:
        original = hits[r.index]
        out.append(replace(original, score=float(r.relevance_score)))
    log.debug("rerank: %d → %d (model=%s)", len(hits), len(out), model)
    return out
