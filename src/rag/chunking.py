"""Document chunking.

Recursive character splitter tuned for academic abstracts + paper bodies.
Returns Chunk dataclasses carrying content + metadata so downstream code
doesn't have to keep two parallel lists in sync.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass(slots=True)
class Chunk:
    content: str
    index: int
    metadata: dict[str, Any] = field(default_factory=dict)


_SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "]


def make_splitter(chunk_size: int = 800, chunk_overlap: int = 120) -> RecursiveCharacterTextSplitter:
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=_SEPARATORS,
        length_function=len,
    )


def chunk_text(
    text: str,
    *,
    metadata: dict[str, Any] | None = None,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[Chunk]:
    if not text or not text.strip():
        return []
    splitter = make_splitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    pieces = splitter.split_text(text)
    base_meta = dict(metadata or {})
    return [
        Chunk(content=p.strip(), index=i, metadata=base_meta.copy())
        for i, p in enumerate(pieces)
        if p.strip()
    ]


def chunk_many(
    docs: Iterable[tuple[str, dict[str, Any]]],
    *,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[Chunk]:
    """Chunk a stream of (text, metadata) pairs. Chunk indexes restart per doc."""
    out: list[Chunk] = []
    for text, meta in docs:
        out.extend(
            chunk_text(text, metadata=meta, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        )
    return out
