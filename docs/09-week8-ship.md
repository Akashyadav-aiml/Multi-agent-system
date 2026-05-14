# Week 8 — Ship It

**Goal:** Wrap the system in a FastAPI service with streaming, build a minimal frontend, deploy somewhere public, write a portfolio-grade README. Make it demoable.

**Time:** 8–12 hours.

**You'll touch:** `src/api/`, a separate frontend folder, deployment configs.

---

## The shipping checklist

A "production-style" project on a resume needs:

- [ ] **Public URL** anyone can hit
- [ ] **Streaming UI** that shows agent progress
- [ ] **Architecture diagram** in the README
- [ ] **Eval numbers** in the README
- [ ] **Cost data** (per-query average)
- [ ] **2-minute Loom demo** linked at the top of the README
- [ ] **Code quality** — typed, formatted, no commented-out blocks
- [ ] **Tests** — at minimum, one integration test that runs end-to-end

Without these, recruiters see "another LangChain tutorial." With them, "someone who can ship."

## Step 1 — FastAPI wrapper

```python
# src/api/main.py
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from src.graph.workflow import app as graph_app

app = FastAPI(title="Deep Research Agent")

class QueryRequest(BaseModel):
    question: str
    thread_id: str | None = None

@app.post("/research")
async def research(req: QueryRequest):
    async def stream():
        config = {"configurable": {"thread_id": req.thread_id or "default"}}
        async for event in graph_app.astream(
            {"question": req.question, "iterations": 0},
            config=config,
            stream_mode="updates",
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")

@app.get("/health")
async def health():
    return {"status": "ok"}
```

Server-Sent Events (SSE) is the simplest streaming protocol — works in plain HTML with `EventSource`. Save WebSockets for when you need bidirectional.

Run locally:

```bash
uvicorn src.api.main:app --reload --port 8000
```

Test:

```bash
curl -N -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"question": "What are recent advances in MoE models?"}'
```

You should see events stream as nodes complete.

## Step 2 — Minimal frontend

You have three options, listed by ROI:

### Option A: Streamlit (90 minutes, ugly but works)

```python
# frontend/app.py
import streamlit as st
import requests
import json

st.title("Deep Research Agent")
question = st.text_input("Your research question:")

if st.button("Research") and question:
    placeholder = st.empty()
    accumulated = ""

    with requests.post(
        "http://localhost:8000/research",
        json={"question": question},
        stream=True,
    ) as r:
        for line in r.iter_lines():
            if line and line.startswith(b"data: "):
                event = json.loads(line[6:])
                accumulated += f"\n\n{event}"
                placeholder.markdown(accumulated)
```

Good enough for a demo. Limited customization.

### Option B: Next.js + Tailwind (1–2 days, looks professional)

A simple App Router page with `useEventSource` consuming `/research`. Pre-built components from shadcn/ui. Deploy to Vercel. This is what you want for the portfolio.

Skeleton structure:

```
frontend/
├── app/
│   ├── page.tsx          # main UI
│   └── api/research/route.ts   # proxy to backend
├── components/
│   ├── question-input.tsx
│   ├── agent-progress.tsx     # shows each node firing
│   └── report-view.tsx
└── ...
```

### Option C: HTML + vanilla JS (2 hours, minimum viable)

A single file with `<EventSource>`. Works. Demos fine.

For Week 8, pick A or C and ship. Upgrade to B in Week 9 if you want.

## Step 3 — Deployment

**Backend (FastAPI + Gemini):** the default Gemini setup is trivial to deploy — the LLM runs on Google's servers, your container just needs Python + the API key.

| Option              | Cost          | Effort     | Good for                       |
| ------------------- | ------------- | ---------- | ------------------------------ |
| Railway / Render    | Free–$5/mo    | Low        | Portfolio default              |
| Fly.io              | Free–$5/mo    | Low        | Global edge, scales to zero    |
| AWS / GCP Run       | Pay-per-req   | Medium     | If you want cloud-native creds |

Set `GOOGLE_API_KEY` as a secret in the host's env. No GPU, no model downloads, no warm-up.

**If you ran Week 8 on Ollama:** swap to a hosted LLM at deploy time — Ollama on a cloud VM needs a GPU ($0.30–1/hr) or accepts much slower CPU inference. Your `make_*_llm()` factory makes the swap a one-line config change. Anthropic Claude or OpenAI also work; recruiters trust hosted models more.

**pgvector:** Neon, Supabase, or Render all offer hosted Postgres with pgvector. Free tiers are generous. Move your local DB by `pg_dump` + restore.

**Frontend:** Vercel (Next.js) or Streamlit Cloud. Free.

## Step 4 — Portfolio README

Replace the existing project README with a portfolio-focused version. Structure:

```markdown
# Deep Research Agent for arXiv

[Architecture diagram image]

A multi-agent research system. Ask a question, get a cited report.

**[▶ 2-min Loom demo](link)**  •  **[Live demo](link)**  •  **[Blog post](link)**

## What it does
[1 paragraph]

## Architecture
[Mermaid diagram with node descriptions]

## Stack
| Layer | Tool |
|-------|------|
| ... | ... |

## Performance
| Metric | Value |
|--------|-------|
| Faithfulness (Ragas) | 0.91 |
| Answer relevancy | 0.87 |
| Context precision | 0.83 |
| Avg latency per query | 12s |
| Avg cost per query | $0.04 |

## What I learned
[3–5 bullets — be specific]

## Running locally
[Brief]
```

The **Performance** and **What I learned** sections are what hiring managers actually read.

## Step 5 — Demo recording

2 minutes max. Show:
1. The architecture diagram (15 sec talkover)
2. Ask a research question (10 sec)
3. Show the streaming UI with agents firing (60 sec)
4. Final report with citations (30 sec)
5. One impressive detail: maybe Langfuse trace, maybe the MCP server in Claude Desktop (15 sec)

Tools: Loom, Tella, or just QuickTime + iMovie.

## Step 6 — Optional polish

- **Write a blog post.** Hashnode/dev.to. Title: "Building a Production Multi-Agent Research System in 8 Weeks." Link to repo. Cross-post to LinkedIn. This generates more recruiter attention than the repo alone.
- **Open-source the MCP server separately.** Pull `src/mcp_server/` into its own repo. Publish to the awesome-mcp-servers list. Free distribution.
- **Submit to /r/LocalLLaMA, Hacker News Show HN.** Genuine traffic, real feedback.

## Checkpoint

Done with Week 8 when:

- [ ] FastAPI service runs locally with `uvicorn`
- [ ] Streaming endpoint works via curl
- [ ] Frontend connects and renders progress
- [ ] Deployed somewhere with a public URL
- [ ] README has architecture diagram, performance table, demo link
- [ ] Loom demo recorded and linked
- [ ] You've sent the link to at least one person and gotten feedback

## Things to try

1. **Multi-tenant.** Add `user_id` to the thread_id; users get isolated histories.
2. **Persistent reports.** Save final reports to Postgres. Add `/history` endpoint.
3. **Slack bot.** Slack slash command → triggers research → posts report. Demonstrates real integration.
4. **PDF export.** Generate a styled PDF of the report. Use `weasyprint` or `reportlab`.

## Common pitfalls

**CORS errors.** Frontend on Vercel, backend on Fly = different origins. Add `CORSMiddleware` to FastAPI with explicit origins.

**Streaming chunks don't render.** Frontend expects `data: ...\n\n` format. Don't forget the trailing double newline.

**Ollama on a deploy VM is slow.** First request loads the model (~10s). Solution: warm-up curl on startup, or just use a cloud model in deploy.

**Recruiters can't run it.** No `Dockerfile`, no `make` command, dependencies broken. Add a top-level `Makefile` with `make up` that does everything.

**README is 12 paragraphs of context.** Rewrite for skim-readers. Bullets, tables, screenshots. Recruiters spend ~30s on each repo.

## Reading

- FastAPI streaming: <https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse>
- LangGraph + FastAPI tutorial: <https://langchain-ai.github.io/langgraph/cloud/deployment/setup/>
- "How to write a great GitHub README" (skim): plenty of good posts

## You're done

Eight weeks. One working, tested, deployed, multi-agent system. That's a portfolio piece, not a tutorial output.

**Next moves:** add a second vertical (legal? medical?), open-source pieces, write about the experience, apply to AI engineering roles.

→ Back to [`README.md`](../README.md) or check out [`RESOURCES.md`](./RESOURCES.md) for further reading.
