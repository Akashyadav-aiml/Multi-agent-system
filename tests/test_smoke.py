"""Smoke tests: imports + cheap pure-Python checks.

Anything that needs a live DB / API key is gated behind env flags so CI
doesn't fail when those aren't configured.
"""
from __future__ import annotations

import os

import pytest


def test_imports_all_modules():
    # If any module has a syntax error or top-level crash, this surfaces it.
    import src.api.main  # noqa: F401
    import src.config  # noqa: F401
    import src.graph.nodes  # noqa: F401
    import src.graph.state  # noqa: F401
    import src.graph.workflow  # noqa: F401
    import src.mcp_server.server  # noqa: F401
    import src.rag.chunking  # noqa: F401
    import src.rag.db  # noqa: F401
    import src.rag.ingest  # noqa: F401
    import src.rag.retriever  # noqa: F401
    import src.tools.arxiv_search  # noqa: F401


def test_chunking_basic():
    from src.rag.chunking import chunk_text

    text = "Sentence one. Sentence two. " * 200
    chunks = chunk_text(text, metadata={"source": "test"}, chunk_size=400, chunk_overlap=80)
    assert chunks, "chunking returned no chunks"
    assert all(c.content for c in chunks)
    assert all(c.metadata["source"] == "test" for c in chunks)
    assert chunks[0].index == 0


def test_chunking_empty():
    from src.rag.chunking import chunk_text

    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_arxiv_tool_schema():
    from src.tools.arxiv_search import ArxivSearchTool

    tool = ArxivSearchTool()
    assert tool.name == "arxiv_search"
    assert "arXiv" in tool.description
    schema = tool.args_schema.model_json_schema()
    assert "query" in schema["properties"]
    assert "max_results" in schema["properties"]


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="DB tests off by default; set RUN_DB_TESTS=1 with pgvector up.",
)
def test_db_ping():
    from src.rag.db import ping

    assert ping(), "pgvector unreachable — is docker compose up?"
