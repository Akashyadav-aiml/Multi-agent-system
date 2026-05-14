"""arXiv research MCP server.

Exposes the same retrieval surface our crew uses, but over the Model Context
Protocol so any MCP client (Claude Desktop, Cursor, our crew via
MCPServerAdapter) can call it.

Run standalone (stdio):
    python -m src.mcp_server.server

Or wire into Claude Desktop via claude_desktop_config.json.
"""
from __future__ import annotations

import logging

import arxiv
from mcp.server.fastmcp import FastMCP

from src.logging_setup import configure_logging
from src.rag.retriever import format_hits_for_llm, vector_search
from src.tools.arxiv_search import ArxivSearchTool

configure_logging()
log = logging.getLogger(__name__)

mcp = FastMCP("arxiv-research")

_arxiv_tool = ArxivSearchTool()
_arxiv_client = arxiv.Client(page_size=10, delay_seconds=1.0, num_retries=3)


@mcp.tool()
def arxiv_search(query: str, max_results: int = 5) -> str:
    """Search arXiv for recent academic papers.

    Use this when the user asks about research, methods, benchmarks, or wants
    citations from primary sources. Returns titles, authors, abstracts, arXiv IDs.

    Args:
        query: Natural-language search query.
        max_results: Number of papers to return (1-20).
    """
    if not 1 <= max_results <= 20:
        raise ValueError("max_results must be between 1 and 20")
    return _arxiv_tool._run(query=query, max_results=max_results)


@mcp.tool()
def fetch_paper(arxiv_id: str) -> str:
    """Fetch a single arXiv paper's metadata + full abstract by ID.

    Args:
        arxiv_id: arXiv ID, e.g. '2501.12345' (no 'arXiv:' prefix, no version suffix).
    """
    arxiv_id = arxiv_id.strip().removeprefix("arXiv:").removeprefix("arxiv:")
    search = arxiv.Search(id_list=[arxiv_id])
    results = list(_arxiv_client.results(search))
    if not results:
        return f"No paper found for arXiv ID {arxiv_id!r}."
    p = results[0]
    authors = ", ".join(a.name for a in p.authors)
    return (
        f"arXiv:{arxiv_id}\n"
        f"Title: {p.title.strip()}\n"
        f"Authors: {authors}\n"
        f"Published: {p.published.date() if p.published else 'unknown'}\n"
        f"Categories: {', '.join(p.categories)}\n"
        f"PDF: {p.pdf_url}\n\n"
        f"Abstract:\n{p.summary.strip()}"
    )


@mcp.tool()
def corpus_search(query: str, top_k: int = 5, min_score: float = 0.0) -> str:
    """Search the LOCAL ingested arXiv corpus via pgvector similarity.

    Use BEFORE arxiv_search for questions likely answerable from already-ingested
    papers — faster and grounded in vetted sources.

    Args:
        query: Question or topic.
        top_k: Number of chunks to return (1-20).
        min_score: Drop hits below this cosine similarity (0.0-1.0).
    """
    if not 1 <= top_k <= 20:
        raise ValueError("top_k must be between 1 and 20")
    if not 0.0 <= min_score <= 1.0:
        raise ValueError("min_score must be between 0.0 and 1.0")
    hits = vector_search(query, top_k=top_k, min_score=min_score)
    return format_hits_for_llm(hits)


def main() -> None:
    log.info("Starting arxiv-research MCP server on stdio")
    mcp.run()


if __name__ == "__main__":
    main()
