"""Ingest pipeline: arXiv search → chunk → embed → write to pgvector.

Idempotent: rerunning the same topic skips already-stored papers and chunks.
Batched embeddings (Google API accepts up to 100 docs/call).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

import arxiv

from src.config import EMBED_DIM, get_embeddings
from src.rag.chunking import Chunk, chunk_text
from src.rag.db import connect

log = logging.getLogger(__name__)

EMBED_BATCH = 64  # well under Google's 100/call cap


@dataclass(slots=True)
class IngestStats:
    papers_seen: int = 0
    papers_inserted: int = 0
    chunks_inserted: int = 0
    skipped: int = 0


def _normalize_id(entry_id: str) -> str:
    """arxiv lib returns 'http://arxiv.org/abs/2501.12345v2'. Strip to '2501.12345'."""
    tail = entry_id.rstrip("/").split("/")[-1]
    if "v" in tail:
        tail = tail.split("v")[0]
    return tail


def _existing_arxiv_ids(conn, ids: list[str]) -> set[str]:
    if not ids:
        return set()
    with conn.cursor() as cur:
        cur.execute("SELECT arxiv_id FROM papers WHERE arxiv_id = ANY(%s)", (ids,))
        return {row[0] for row in cur.fetchall()}


def _insert_paper(conn, paper: arxiv.Result) -> bool:
    """Insert paper row. Returns True if newly inserted, False if it already existed."""
    arxiv_id = _normalize_id(paper.entry_id)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO papers (arxiv_id, title, authors, abstract, published_at, pdf_url, categories)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (arxiv_id) DO NOTHING
            """,
            (
                arxiv_id,
                paper.title.strip(),
                [a.name for a in paper.authors],
                (paper.summary or "").strip(),
                paper.published.replace(tzinfo=None) if paper.published else None,
                paper.pdf_url,
                paper.categories,
            ),
        )
        return cur.rowcount > 0


def _insert_chunks(conn, arxiv_id: str, chunks: list[Chunk], embeddings: list[list[float]]) -> int:
    if not chunks:
        return 0
    if len(chunks) != len(embeddings):
        raise RuntimeError(f"chunks/embeddings size mismatch: {len(chunks)} vs {len(embeddings)}")
    rows = [
        (arxiv_id, c.index, c.content, emb, c.metadata)
        for c, emb in zip(chunks, embeddings, strict=True)
    ]
    with conn.cursor() as cur:
        # COPY would be faster, but executemany keeps the code simple and works fine at <10k chunks.
        cur.executemany(
            """
            INSERT INTO chunks (arxiv_id, chunk_index, content, embedding, metadata)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (arxiv_id, chunk_index) DO NOTHING
            """,
            rows,
        )
        return cur.rowcount


def _batched(seq: list, n: int) -> Iterable[list]:
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def ingest_topic(
    topic: str,
    *,
    limit: int = 50,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> IngestStats:
    """Search arXiv for `topic`, ingest up to `limit` papers."""
    stats = IngestStats()

    log.info("Searching arXiv: topic=%r limit=%d", topic, limit)
    search = arxiv.Search(query=topic, max_results=limit, sort_by=arxiv.SortCriterion.Relevance)
    client = arxiv.Client(page_size=min(limit, 50), delay_seconds=3.0, num_retries=3)
    papers = list(client.results(search))
    stats.papers_seen = len(papers)
    log.info("arXiv returned %d papers", len(papers))

    if not papers:
        return stats

    ids = [_normalize_id(p.entry_id) for p in papers]
    embeddings_model = get_embeddings()

    with connect() as conn:
        already = _existing_arxiv_ids(conn, ids)
        log.info("Skipping %d already-ingested papers", len(already))

        for paper in papers:
            arxiv_id = _normalize_id(paper.entry_id)
            if arxiv_id in already:
                stats.skipped += 1
                continue

            newly_inserted = _insert_paper(conn, paper)
            if newly_inserted:
                stats.papers_inserted += 1

            # We chunk the abstract; in Week 6 you can add full PDF text here.
            text = (paper.summary or "").strip()
            meta = {
                "arxiv_id": arxiv_id,
                "title": paper.title.strip(),
                "published": paper.published.date().isoformat() if paper.published else None,
                "source": "abstract",
            }
            chunks = chunk_text(text, metadata=meta, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            if not chunks:
                conn.commit()
                continue

            all_embeddings: list[list[float]] = []
            for batch in _batched([c.content for c in chunks], EMBED_BATCH):
                vecs = embeddings_model.embed_documents(batch)
                # Sanity: dimension must match the column
                if vecs and len(vecs[0]) != EMBED_DIM:
                    raise RuntimeError(
                        f"Embedding dim {len(vecs[0])} != EMBED_DIM {EMBED_DIM}. "
                        "Rebuild the chunks table or update EMBED_DIM."
                    )
                all_embeddings.extend(vecs)

            inserted = _insert_chunks(conn, arxiv_id, chunks, all_embeddings)
            stats.chunks_inserted += inserted
            conn.commit()
            log.info("Ingested %s: %d chunks", arxiv_id, inserted)

    log.info(
        "Done. seen=%d inserted=%d skipped=%d chunks=%d",
        stats.papers_seen,
        stats.papers_inserted,
        stats.skipped,
        stats.chunks_inserted,
    )
    return stats
