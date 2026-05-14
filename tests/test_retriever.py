"""Unit tests for src.rag.retriever — DB and embeddings mocked."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.rag import retriever as r


def _fake_rows():
    return [
        ("2501.00001", 0, "alpha content", 0.92, "Alpha Paper", datetime(2025, 1, 1), {"k": "v"}),
        ("2501.00002", 0, "beta content", 0.81, "Beta Paper", datetime(2025, 2, 1), {}),
    ]


@contextmanager
def _fake_connect():
    conn = MagicMock(name="conn")
    cur = MagicMock(name="cur")
    cur.fetchall.return_value = _fake_rows()
    cur.__enter__.return_value = cur
    cur.__exit__.return_value = None
    conn.cursor.return_value = cur
    yield conn


@pytest.fixture(autouse=True)
def _patch_db_and_embeddings():
    with patch.object(r, "connect", _fake_connect), \
         patch.object(r, "get_embeddings") as ge:
        ge.return_value.embed_query.return_value = [0.0] * 768
        yield


def test_empty_query_short_circuits():
    assert r.vector_search("") == []
    assert r.vector_search("   ") == []


def test_returns_typed_hits_no_rerank():
    hits = r.vector_search("transformers", top_k=5, rerank=False)
    assert len(hits) == 2
    assert all(isinstance(h, r.Hit) for h in hits)
    assert hits[0].arxiv_id == "2501.00001"
    assert hits[0].title == "Alpha Paper"
    assert hits[0].score == pytest.approx(0.92)
    assert hits[0].published == "2025-01-01"


def test_min_score_filters_low_hits():
    hits = r.vector_search("transformers", top_k=5, min_score=0.9, rerank=False)
    assert len(hits) == 1
    assert hits[0].arxiv_id == "2501.00001"


def test_published_after_adds_clause():
    captured: list[str] = []

    @contextmanager
    def _spy_connect():
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchall.return_value = _fake_rows()
        cur.__enter__.return_value = cur
        cur.__exit__.return_value = None

        def _exec(sql, params):
            captured.append(sql)
        cur.execute.side_effect = _exec
        conn.cursor.return_value = cur
        yield conn

    with patch.object(r, "connect", _spy_connect):
        r.vector_search("q", top_k=3, rerank=False, published_after="2025-01-15")
    assert any("published_at" in s for s in captured)
    assert any("<=>" in s for s in captured)  # cosine distance operator


def test_format_hits_for_llm_empty_and_full():
    assert "No relevant" in r.format_hits_for_llm([])
    hits = r.vector_search("anything", top_k=2, rerank=False)
    formatted = r.format_hits_for_llm(hits)
    assert "arXiv:2501.00001" in formatted
    assert "score=" in formatted
