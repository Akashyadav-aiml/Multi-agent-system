# Deep Research Agent — arXiv Edition

A production-style multi-agent system that takes a research question (e.g. *"What are the latest approaches to mitigating hallucinations in RAG?"*) and produces a cited research report by coordinating multiple specialized agents.

**Stack:** CrewAI → LangGraph, pgvector, Google Gemini (free tier), MCP, Ragas.

**Why Gemini:** Google AI Studio gives 1,500 free requests/day on Gemini 2.5 Flash — a frontier-class model with much better tool-calling than 8B open models. Embeddings are free on the same key. Total cost for the whole 8-week project: **$0**. No credit card required.

> Prefer fully local? See the [Ollama appendix](./docs/APPENDIX-OLLAMA.md) — swap two config values and it all works offline.

---

## 📖 Start here

Full week-by-week learning docs live in [`docs/`](./docs/). Read in order:

1. [Project overview & architecture](./docs/00-overview.md)
2. [Environment setup](./docs/01-setup.md)
3. [Week 1 — Tool calling](./docs/02-week1-tool-calling.md)
4. [Week 2 — Multi-agent crew](./docs/03-week2-crew.md)
5. [Week 3 — RAG & vector DB](./docs/04-week3-rag.md)
6. [Week 4 — MCP server](./docs/05-week4-mcp.md)
7. [Week 5 — LangGraph](./docs/06-week5-langgraph.md)
8. [Week 6 — Evaluation](./docs/07-week6-evals.md)
9. [Week 7 — Optimization](./docs/08-week7-optimization.md)
10. [Week 8 — Ship](./docs/09-week8-ship.md)

Reference: [Glossary](./docs/GLOSSARY.md) • [Curated resources](./docs/RESOURCES.md)

---

## What you'll learn (and where)

| Concept                     | Lives in                                       | Week |
| --------------------------- | ---------------------------------------------- | ---- |
| Tool calling                | `src/tools/`                                   | 1    |
| Agent roles & crews         | `src/agents/crew.py`                           | 2    |
| RAG + vector DB             | `src/rag/`                                     | 3    |
| MCP server (your own tool)  | `src/mcp_server/`                              | 4    |
| Graph orchestration         | `src/graph/workflow.py`                        | 5    |
| Evaluation (Ragas/Langfuse) | `src/evals/`                                   | 6    |
| Cost & latency optimization | `src/config.py` (model tiers)                  | 7    |
| Ship (API + UI)             | `src/api/`, separate frontend repo             | 8    |

---

## Prerequisites

1. **Python 3.11+**
2. **Docker** (for pgvector — the only thing that runs locally)
3. **Google AI Studio API key** — sign up free at <https://aistudio.google.com/apikey>. No credit card.
4. **Any laptop.** No GPU, no big RAM, no model downloads. The LLM runs on Google's servers.

---

## Setup (one time)

```bash
# 1. Clone & enter
cd deep-research-agent

# 2. Virtual env
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install deps
pip install -r requirements.txt

# 4. Start pgvector
docker compose up -d
# Wait ~5 sec, then init the schema:
docker exec -i deep-research-pg psql -U postgres -d multi_agent_system < scripts/setup_db.sql

# 5. Env vars (add your Gemini API key)
cp .env.example .env
# Edit .env and paste your GOOGLE_API_KEY

# 6. Verify
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('OK' if os.getenv('GOOGLE_API_KEY') else 'Missing GOOGLE_API_KEY')"
```

---

## Weekly progression

### Week 1 — One agent, two tools

Goal: feel tool-calling work end-to-end before any orchestration.

```bash
python scripts/run_week1.py "transformer architecture improvements 2025"
```

You'll see the agent decide when to call the arXiv tool vs. answer from its own knowledge. Read the trace. Notice what it gets wrong.

### Week 2 — A crew (Planner → Researcher → Writer)

```bash
python scripts/run_week2.py "Compare LoRA vs full fine-tuning for LLMs"
```

Sequential crew. No RAG yet. The output will be passable but generic. That's the lesson.

### Week 3 — Add RAG

Ingest 100 papers, then ask questions grounded in them:

```bash
python scripts/run_week3_ingest.py --topic "retrieval augmented generation" --limit 100
python scripts/run_week3.py "What are the most effective reranking strategies for RAG?"
```

The Retrieval agent now grounds answers in your corpus. Faithfulness jumps.

### Week 4 — Write your own MCP server

Expose arXiv as an MCP tool that *any* agent (yours, Claude Desktop, Cursor) can use:

```bash
python -m src.mcp_server.server
```

This single file on your GitHub is more impressive than the whole crew. Most candidates have never built one.

### Week 5 — Migrate to LangGraph

Rebuild the crew as a state graph with conditional edges, checkpoints, and a fact-checker loop:

```bash
python scripts/run_week5.py "your question"
```

You'll *get* why LangGraph exists when you add the fact-checker → writer loop and CrewAI can't express it cleanly.

### Week 6 — Evals

```bash
python -m src.evals.ragas_eval
```

Build a 30-question golden set. Measure faithfulness, answer relevancy, context precision. Iterate until ≥0.85.

### Week 7 — Model tiering

In `src/config.py`, route by task:
- `gemini-2.5-flash-lite` → query classification, routing
- `gemini-2.5-flash` → drafting, retrieval evaluation, synthesis
- (Later, optional) `gemini-2.5-pro` or Claude/GPT-4 → final synthesis only

Measure cost per completed task, not tokens.

### Week 8 — Ship

FastAPI backend in `src/api/`, Next.js or Streamlit frontend in a separate repo. Deploy on Railway / Fly / Render. Write the README with architecture diagram and eval numbers.

---

## Project structure

```
deep-research-agent/
├── docker-compose.yml         # pgvector
├── requirements.txt
├── .env.example
├── scripts/
│   ├── setup_db.sql           # pgvector schema
│   ├── run_week1.py           # single agent
│   ├── run_week3_ingest.py    # populate vector DB
│   └── ...
└── src/
    ├── config.py              # env loading, LLM factory, model tiers
    ├── tools/
    │   └── arxiv_search.py    # arXiv search as a CrewAI tool
    ├── agents/
    │   └── crew.py            # Week 2: CrewAI crew
    ├── rag/
    │   ├── chunking.py        # semantic chunking
    │   ├── ingest.py          # download papers → chunk → embed → store
    │   └── retriever.py       # query + rerank, exposed as a tool
    ├── mcp_server/
    │   └── server.py          # Week 4: arXiv as an MCP server
    ├── graph/
    │   └── workflow.py        # Week 5: LangGraph state machine
    └── evals/
        └── ragas_eval.py      # Week 6: golden set evals
```

---

## Reading order (do NOT skip)

In this exact sequence, before/during the corresponding week:

1. **LangChain Agents concept page** → `python.langchain.com/docs/concepts/agents/`
2. **CrewAI quickstart** → `docs.crewai.com/quickstart`
3. **CrewAI examples folder on GitHub** → `github.com/crewAIInc/crewAI/tree/main/examples` (worth more than any blog post)
4. **MCP spec** → `modelcontextprotocol.io/specification`
5. **Anthropic's reference MCP servers** → `github.com/modelcontextprotocol/servers`
6. **LangGraph concepts** → `langchain-ai.github.io/langgraph/concepts/`
7. **Ragas docs** → `docs.ragas.io`

Each is ~30–60 minutes. Don't watch YouTube before reading these.

---

## Troubleshooting

**`API key not valid`.** Double-check `GOOGLE_API_KEY` in `.env`. Get a fresh key from <https://aistudio.google.com/apikey>.

**`429 RESOURCE_EXHAUSTED`.** Per-minute rate limit hit (~10–15 RPM on free tier). Wait 60 seconds or stack a second provider (see [`docs/APPENDIX-OLLAMA.md`](./docs/APPENDIX-OLLAMA.md) for hybrid setups).

**CrewAI hangs.** Almost always a tool that loops. Set `max_iter=5` on agents during dev.

**pgvector "extension not found".** You forgot to run `setup_db.sql`. Re-run step 4 of setup.

**Embedding dimension mismatch.** `text-embedding-004` returns 768-dim. If you switch embedding models, update the `vector(768)` column in `setup_db.sql`.

---

## What "done" looks like

By Week 8, this repo should have:

- ✅ A working multi-agent system answering arXiv research questions
- ✅ pgvector with 500+ papers ingested
- ✅ One MCP server you can demo with `npx @modelcontextprotocol/inspector`
- ✅ A LangGraph workflow with at least one conditional loop
- ✅ Ragas scores ≥0.85 faithfulness and ≥0.80 context precision on a golden set
- ✅ A README with an architecture diagram (use Excalidraw or Mermaid)
- ✅ A 2-minute Loom demo linked at the top of the README

That's a senior-level portfolio piece, not a tutorial project.
