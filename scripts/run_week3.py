"""Week 3: crew with RAG.

Same 3-agent crew as Week 2, but the Researcher now has BOTH tools:
arxiv_search (live API) and vector_search (local corpus). The agent decides
which to use per sub-question.

Usage:
    python scripts/run_week3.py "What are the most effective reranking strategies for RAG?"
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from crewai import Agent, Crew, Process, Task

from src.config import make_crewai_llm
from src.logging_setup import configure_logging
from src.rag.retriever import VectorSearchTool
from src.tools.arxiv_search import ArxivSearchTool


def build_crew() -> Crew:
    llm = make_crewai_llm("main")

    planner = Agent(
        role="Research Planner",
        goal="Decompose a question into 3-5 specific sub-questions.",
        backstory=(
            "You are a meticulous research lead. You break vague questions into "
            "concrete, searchable sub-questions and decide what evidence would settle each."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    researcher = Agent(
        role="Academic Researcher",
        goal=(
            "For each sub-question, retrieve relevant evidence. Prefer vector_search "
            "(local corpus) first; fall back to arxiv_search for fresh or out-of-corpus topics."
        ),
        backstory=(
            "You are a careful academic researcher. You cite arXiv IDs precisely and "
            "never invent results. You always check the local corpus first because "
            "it is curated; you use arxiv_search only when the corpus comes up short."
        ),
        llm=llm,
        tools=[VectorSearchTool(), ArxivSearchTool()],
        verbose=True,
        max_iter=10,
        allow_delegation=False,
    )

    writer = Agent(
        role="Technical Writer",
        goal="Synthesize the research notes into a clear, cited report.",
        backstory=(
            "You write like a senior engineer briefing an executive: structured, "
            "concrete, no hedging. Every claim has a [arXiv:id] citation."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    plan_task = Task(
        description=(
            "User's research question: {question}\n\n"
            "Decompose this into 3-5 specific sub-questions. Number them. "
            "For each, briefly note what kind of evidence would answer it."
        ),
        expected_output="A numbered list of 3-5 sub-questions, each with a 1-sentence evidence note.",
        agent=planner,
    )

    research_task = Task(
        description=(
            "Using the sub-questions, gather evidence:\n"
            "  1. For each sub-question, call `vector_search` first.\n"
            "  2. If the local hits are weak (low score or off-topic), call `arxiv_search`.\n"
            "  3. Summarize 2-4 supporting findings per sub-question.\n"
            "Cite arXiv IDs precisely."
        ),
        expected_output=(
            "For each sub-question: a short paragraph synthesizing findings, with arXiv IDs in [brackets]."
        ),
        agent=researcher,
        context=[plan_task],
    )

    write_task = Task(
        description=(
            "Write the final research report answering: {question}\n\n"
            "Structure:\n"
            "  1. Direct answer (2-3 sentences)\n"
            "  2. Key findings (one section per sub-question)\n"
            "  3. Open questions\n"
            "  4. References (every arXiv ID cited)\n\n"
            "Markdown. Cite inline as [arXiv:2501.12345]."
        ),
        expected_output="A complete markdown research report (600-1000 words).",
        agent=writer,
        context=[research_task],
    )

    return Crew(
        agents=[planner, researcher, writer],
        tasks=[plan_task, research_task, write_task],
        process=Process.sequential,
        verbose=True,
    )


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python scripts/run_week3.py "your research question"')
        sys.exit(1)

    configure_logging()
    question = " ".join(sys.argv[1:])

    crew = build_crew()
    result = crew.kickoff(inputs={"question": question})

    print("\n" + "=" * 70)
    print("FINAL REPORT")
    print("=" * 70)
    print(result)


if __name__ == "__main__":
    main()
