# Learning Resources

Curated, ROI-ranked. Read top-down; the first 5 will get you 80% of the way.

## Tier 1 — Read these first (3–5 hours total)

These are the most useful single docs on the internet for this project. Read each one fully before its corresponding week.

1. **LangChain Agents Concept** — <https://python.langchain.com/docs/concepts/agents/>
   *Read before Week 1.* Explains what an agent actually is. Short.

2. **CrewAI Quickstart + Core Concepts** — <https://docs.crewai.com/quickstart>
   *Read before Week 2.* The "Agents," "Tasks," and "Crews" pages.

3. **LangChain RAG Concept** — <https://python.langchain.com/docs/concepts/rag/>
   *Read before Week 3.* Best single overview.

4. **Anthropic — Contextual Retrieval** — <https://www.anthropic.com/news/contextual-retrieval>
   *Read during Week 3.* Production-quality patterns for chunking and retrieval.

5. **MCP Specification** — <https://modelcontextprotocol.io/specification>
   *Read before Week 4.* The protocol is small; understand it cover-to-cover.

6. **LangGraph Concepts** — <https://langchain-ai.github.io/langgraph/concepts/>
   *Read before Week 5.* All the concept pages, in order.

7. **Ragas Metrics** — <https://docs.ragas.io/en/latest/concepts/metrics/index.html>
   *Read before Week 6.* What each metric measures, and why.

## Tier 2 — Worth your time

8. **CrewAI examples folder** — <https://github.com/crewAIInc/crewAI/tree/main/examples>
   Pick 2–3 examples and read them fully. Worth more than blog tutorials.

9. **Anthropic reference MCP servers** — <https://github.com/modelcontextprotocol/servers>
   Real production-grade MCP code. Read the `filesystem`, `github`, `postgres` servers.

10. **LangGraph multi-agent tutorial** — <https://langchain-ai.github.io/langgraph/tutorials/multi_agent/>
    The canonical multi-agent patterns in LangGraph.

11. **pgvector README** — <https://github.com/pgvector/pgvector>
    Especially the index tuning section.

12. **Anthropic prompt engineering docs** — <https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview>
    Even though you're using local LLMs, the principles transfer.

## Tier 3 — Foundational papers

Skim, don't try to absorb everything. These give vocabulary for interviews.

- **ReAct: Synergizing Reasoning and Acting** — <https://arxiv.org/abs/2210.03629>
  The pattern every agent framework implements.

- **Retrieval-Augmented Generation (the original)** — <https://arxiv.org/abs/2005.11401>
  Where RAG comes from. Skim section 2–3.

- **Self-RAG: Self-reflective retrieval** — <https://arxiv.org/abs/2310.11511>
  Agentic RAG before the name existed.

- **Reflexion: Verbal RL via reflection** — <https://arxiv.org/abs/2303.11366>
  The fact-check / retry loop you build in Week 5.

- **Contextual Retrieval (Anthropic)** — search "anthropic contextual retrieval"
  Practical 2024+ retrieval improvements.

## Tier 4 — Newsletters & ongoing reading

- **LangChain blog** — actually-good, technical
- **Anthropic Engineering blog** — when they post, read it
- **The AI Engineer (Latent Space)** — podcast, weekly newsletter, both excellent
- **Hacker News** — search "Show HN agent" for current builds

## Tier 5 — Courses (only if you're a "video learner")

Skip these if you can absorb text. They're slower per concept.

- **DeepLearning.AI short courses** — free, 1–2 hours each. The CrewAI, LangGraph, and MCP ones are decent: <https://www.deeplearning.ai/short-courses/>
- **IBM RAG and Agentic AI Capstone** (Coursera) — paid, covers similar ground to this project
- **Hugging Face Agents Course** — free, code-heavy, good

## What NOT to read

- **Random Medium articles with "Build an agent in 5 minutes"** — usually wrong by the time you read them. Frameworks move fast.
- **Twitter threads claiming "the best agent framework"** — marketing, not engineering.
- **AutoGPT tutorials** — historical interest only; AutoGPT lost relevance.
- **Old LangChain blog posts (pre-LCEL)** — the API changed; following old posts will frustrate you.

## How to read efficiently

For each tier-1 doc:
1. Read top to bottom once at full speed. Don't try to understand everything.
2. Identify the 3 hardest sentences. Re-read those.
3. Try to write 3 sentences in your own words summarizing the doc. If you can't, re-read.
4. Move on. You'll absorb more on the second pass next week.

Skipping the docs and watching YouTube instead **feels** faster but creates worse intuition. The text is denser per minute.

→ Back to [`README.md`](../README.md).
