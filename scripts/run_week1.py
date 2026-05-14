"""
Week 1: ONE agent, ONE tool. Run this first.

Goal: see tool calling work end-to-end with Ollama before any orchestration.

Usage:
    python scripts/run_week1.py "transformer architecture improvements 2025"
"""
from __future__ import annotations

import sys

from crewai import Agent, Crew, Process, Task

# So `python scripts/run_week1.py ...` works from project root
sys.path.insert(0, ".")

from src.config import make_crewai_llm
from src.tools.arxiv_search import ArxivSearchTool


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python scripts/run_week1.py "your research question"')
        sys.exit(1)

    question = " ".join(sys.argv[1:])

    researcher = Agent(
        role="Research Assistant",
        goal="Answer the user's research question by finding relevant arXiv papers.",
        backstory=(
            "You are a careful research assistant. You search arXiv when you need "
            "evidence, and you cite papers by arXiv ID."
        ),
        llm=make_crewai_llm("main"),
        tools=[ArxivSearchTool()],
        verbose=True,
        max_iter=5,
    )

    task = Task(
        description=f"Research question: {question}\n\nFind 3-5 relevant papers and summarize what they say.",
        expected_output="A short answer (200-400 words) with arXiv IDs cited in [brackets].",
        agent=researcher,
    )

    crew = Crew(agents=[researcher], tasks=[task], process=Process.sequential, verbose=True)
    result = crew.kickoff()

    print("\n" + "=" * 70)
    print("FINAL ANSWER")
    print("=" * 70)
    print(result)


if __name__ == "__main__":
    main()
