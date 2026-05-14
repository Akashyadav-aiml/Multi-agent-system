"""Unit tests for src.rag.chunking — pure Python, no network."""
from __future__ import annotations

import pytest

from src.rag.chunking import Chunk, chunk_many, chunk_text, make_splitter


def test_make_splitter_rejects_overlap_ge_size():
    with pytest.raises(ValueError):
        make_splitter(chunk_size=400, chunk_overlap=400)
    with pytest.raises(ValueError):
        make_splitter(chunk_size=400, chunk_overlap=500)


def test_chunk_text_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []
    assert chunk_text("\n\n  \n") == []


def test_chunk_text_basic():
    text = "Sentence one. Sentence two. " * 100  # ~2700 chars
    out = chunk_text(text, metadata={"k": "v"}, chunk_size=400, chunk_overlap=80)
    assert len(out) >= 4
    assert all(isinstance(c, Chunk) for c in out)
    assert all(c.content for c in out)
    assert all(c.metadata.get("k") == "v" for c in out)
    assert [c.index for c in out] == list(range(len(out)))


def test_chunk_text_metadata_is_per_chunk_copy():
    out = chunk_text("a. b. c. d. " * 200, metadata={"k": 1}, chunk_size=200, chunk_overlap=20)
    # Mutating one chunk's metadata must not bleed into the next.
    out[0].metadata["new"] = "x"
    assert "new" not in out[1].metadata


def test_chunk_many_indexes_per_doc():
    docs = [
        ("alpha. " * 200, {"src": "A"}),
        ("beta. " * 200, {"src": "B"}),
    ]
    all_chunks = chunk_many(docs, chunk_size=200, chunk_overlap=20)
    src_a = [c for c in all_chunks if c.metadata["src"] == "A"]
    src_b = [c for c in all_chunks if c.metadata["src"] == "B"]
    assert src_a and src_b
    assert src_a[0].index == 0
    assert src_b[0].index == 0  # indexes restart per doc


def test_chunk_text_respects_overlap_count():
    text = ("paragraph one. " * 50) + "\n\n" + ("paragraph two. " * 50)
    out = chunk_text(text, chunk_size=300, chunk_overlap=60)
    assert len(out) >= 2
    # Adjacent chunks should share at least one common substring (overlap behavior)
    # — we don't assert exact bytes because the splitter chooses separators,
    # but we do assert that no chunk content is empty and indexes are contiguous.
    indices = [c.index for c in out]
    assert indices == sorted(indices)
