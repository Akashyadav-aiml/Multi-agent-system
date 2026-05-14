"""
Week 2: a 3-agent CrewAI crew (Planner → Researcher → Writer).

This is the textbook CrewAI pattern: agents have role/goal/backstory, tasks
declare what they expect, the crew runs them sequentially. No RAG yet —
that comes in Week 3 when we add a Retrieval agent and bind a vector-search tool.

Read the comments. Every design choice here is something you'll need to
defend in an interview.
"""
from __future__ import annotations

from crewai import Agent, Crew, Process, Task

from src.config import make_crewai_llm
from src.tools.arxiv_search import ArxivSearchTool


def build_crew() -> Crew:
    llm = make_crewai_llm("main")
    arxiv_tool = ArxivSearchTool()

    # --- Agent 1: Planner -------------------------------------------------
    # Why a planner? Without one, the Researcher tends to do one shallow
    # search and stop. The planner forces an explicit decomposition.
    planner = Agent(
        role="Research Planner",
        goal=(
            "Decompose a user's research question into 3-5 specific sub-questions "
            "that, taken together, fully answer the original question."
        ),
        backstory=(
            "You are a meticulous research lead. You never accept vague questions. "
            "You break them down into concrete, searchable sub-questions and "
            "decide what evidence would settle each one."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,   # Planner doesn't call tools or delegate
    )

    # --- Agent 2: Researcher ----------------------------------------------
    # This is where tool calling lives. The agent decides when to call arxiv_search,
    # reads the results, and decides whether to search again.
    researcher = Agent(
        role="Academic Researcher",
        goal=(
            "For each sub-question, find the most relevant recent papers on arXiv "
            "and extract the key findings."
        ),
        backstory=(
            "You are a careful academic researcher. You prefer recent papers, "
            "cite arXiv IDs precisely, and never invent results. If you can't "
            "find good evidence, you say so."
        ),
        llm=llm,
        tools=[arxiv_tool],
        verbose=True,
        max_iter=8,                # Cap reasoning loops — agents WILL spiral
        allow_delegation=False,
    )

    # --- Agent 3: Writer --------------------------------------------------
    writer = Agent(
        role="Technical Writer",
        goal=(
            "Synthesize the research notes into a clear, well-structured report "
            "with inline citations to arXiv IDs."
        ),
        backstory=(
            "You write like a senior engineer briefing a busy executive: "
            "structured, concrete, no hedging. Every claim has a citation."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    # --- Tasks ------------------------------------------------------------
    # Tasks describe deliverables. The `expected_output` is critical — it's
    # how the LLM knows what "done" looks like.
    plan_task = Task(
        description=(
            "User's research question: {question}\n\n"
            "Decompose this into 3-5 specific sub-questions. Number them. "
            "For each, briefly explain what kind of evidence would answer it."
        ),
        expected_output=(
            "A numbered list of 3-5 sub-questions, each with a 1-sentence "
            "note on what evidence is needed."
        ),
        agent=planner,
    )

    research_task = Task(
        description=(
            "Using the sub-questions from the planner, search arXiv to find "
            "relevant papers. For each sub-question, find 2-4 papers and "
            "summarize their key findings. Cite arXiv IDs."
        ),
        expected_output=(
            "For each sub-question: a short paragraph synthesizing findings "
            "across the cited papers, with arXiv IDs in [brackets]."
        ),
        agent=researcher,
        context=[plan_task],   # depends on planner's output
    )

    write_task = Task(
        description=(
            "Write the final research report answering the original question: "
            "{question}\n\n"
            "Structure:\n"
            "  1. Direct answer (2-3 sentences)\n"
            "  2. Key findings (one section per sub-question)\n"
            "  3. Open questions / what's unclear\n"
            "  4. References (list every arXiv ID cited)\n\n"
            "Use markdown. Cite inline like [arXiv:2501.12345]."
        ),
        expected_output="A complete markdown research report (500-900 words).",
        agent=writer,
        context=[research_task],
    )

    return Crew(
        agents=[planner, researcher, writer],
        tasks=[plan_task, research_task, write_task],
        process=Process.sequential,
        verbose=True,
    )


def run(question: str) -> str:
    crew = build_crew()
    result = crew.kickoff(inputs={"question": question})
    return str(result)
