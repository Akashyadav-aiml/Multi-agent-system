"""
arXiv search tool for CrewAI agents.

Reference implementation showing the right way to expose a Python function
as a tool: typed args via Pydantic, clear description (the LLM reads it!),
deterministic output format.
"""
from __future__ import annotations

from typing import Type

import arxiv
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ArxivSearchInput(BaseModel):
    """Args schema — CrewAI/LiteLLM uses this to build the JSON schema the LLM sees."""

    query: str = Field(
        ...,
        description="Natural-language search query. Examples: "
                    "'transformer mixture of experts', 'rag reranking strategies'.",
    )
    max_results: int = Field(
        default=5,
        description="Number of papers to return. Keep small (3-8) to avoid context bloat.",
        ge=1,
        le=20,
    )


class ArxivSearchTool(BaseTool):
    """Search arXiv for academic papers matching a query.

    Returns a structured text block the LLM can read directly. The description
    below is what the model sees when deciding whether to call this tool — keep
    it specific and actionable.
    """

    name: str = "arxiv_search"
    description: str = (
        "Search arXiv for recent academic papers. Use this when the user asks "
        "about research, methods, benchmarks, or wants citations from primary "
        "sources. Returns titles, authors, abstracts, and arXiv IDs."
    )
    args_schema: Type[BaseModel] = ArxivSearchInput

    def _run(self, query: str, max_results: int = 5) -> str:
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        client = arxiv.Client(page_size=max_results, delay_seconds=1.0)
        results = list(client.results(search))

        if not results:
            return f"No arXiv papers found for query: {query!r}"

        lines = [f"Found {len(results)} papers for {query!r}:\n"]
        for i, r in enumerate(results, 1):
            arxiv_id = r.entry_id.split("/")[-1]  # e.g. "2501.12345v1"
            authors = ", ".join(a.name for a in r.authors[:3])
            if len(r.authors) > 3:
                authors += f", +{len(r.authors) - 3} more"
            # Truncate abstract to keep prompt manageable
            abstract = r.summary.strip().replace("\n", " ")
            if len(abstract) > 500:
                abstract = abstract[:497] + "..."

            lines.append(
                f"[{i}] arXiv:{arxiv_id}\n"
                f"    Title: {r.title.strip()}\n"
                f"    Authors: {authors}\n"
                f"    Published: {r.published.date()}\n"
                f"    Abstract: {abstract}\n"
                f"    PDF: {r.pdf_url}\n"
            )

        return "\n".join(lines)
