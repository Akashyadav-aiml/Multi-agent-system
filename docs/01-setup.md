# 01 — Setup

Everything in this guide takes ~15 minutes (faster than the Ollama path because there's nothing to download). Do not skip the verification steps.

## What you need

- **Python 3.11 or 3.12** — not 3.13 yet (some agent libs lag)
- **Docker** — for pgvector. Docker Desktop on Mac/Windows, `docker.io` on Linux.
- **A Google account** — for the free Gemini API key.

No GPU needed. No 16 GB RAM minimum. Any laptop works because the LLM runs on Google's servers, not yours.

## Step 1 — Get your free Gemini API key

1. Go to <https://aistudio.google.com/apikey>
2. Sign in with any Google account
3. Click "Create API key" → select or create a project → copy the key

**No credit card required.** Your free tier (as of 2026):

| Model                     | Daily limit       | Per-minute |
| ------------------------- | ----------------- | ---------- |
| `gemini-2.5-flash`        | 1,500 requests    | ~10 RPM    |
| `gemini-2.5-flash-lite`   | ~1,500 requests   | ~15 RPM    |
| `text-embedding-004`      | Unlimited (free)  | high       |

For this project you'll use ~10–30 requests per crew run, so 1,500/day = ~50–150 runs per day. More than you need.

## Step 2 — Install Docker

```bash
docker --version
# Docker version 24+ is fine
```

If missing, install from <https://docker.com>.

## Step 3 — Clone & enter the project

```bash
cd ~/projects
cd deep-research-agent
```

## Step 4 — Python environment

```bash
python --version    # 3.11.x or 3.12.x

python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements.txt
```

Expect 2–3 minutes. CrewAI pulls a lot of deps.

## Step 5 — Start pgvector

```bash
docker compose up -d

# Wait ~5 seconds for postgres to be ready, then:
docker exec -i deep-research-pg psql -U postgres -d research < scripts/setup_db.sql
```

**Verify:**

```bash
docker exec -it deep-research-pg psql -U postgres -d research -c "\dt"
# Should show 'papers' and 'chunks' tables
```

```bash
docker exec -it deep-research-pg psql -U postgres -d research -c "SELECT extname FROM pg_extension;"
# Should include 'vector'
```

## Step 6 — Environment variables

```bash
cp .env.example .env
```

Open `.env` in your editor and paste your Gemini API key:

```bash
GOOGLE_API_KEY=AIza...your-key-here...
```

Everything else uses sensible defaults (pgvector on `localhost:5432`, etc.).

**Verify:**

```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); k = os.getenv('GOOGLE_API_KEY'); print('OK' if k and k.startswith('AIza') else 'Key missing or wrong format')"
```

## Step 7 — Smoke test

Run Week 1:

```bash
python scripts/run_week1.py "transformer architecture improvements 2025"
```

You should see:
1. The agent reasoning (verbose=True prints its thinking)
2. A call to the `arxiv_search` tool
3. A formatted answer with arXiv IDs

If you see that, **setup is done.** Move to `02-week1-tool-calling.md`.

---

## Troubleshooting

### `API key not valid` / `400 INVALID_ARGUMENT`
Re-copy the key from <https://aistudio.google.com/apikey>. Common mistakes:
- Pasted a trailing space or newline
- Used a Google Cloud / Vertex AI key instead of AI Studio key (different endpoints)
- Project doesn't have Generative Language API enabled — go enable it

### `429 RESOURCE_EXHAUSTED`
You hit the per-minute rate limit (free tier ~10–15 RPM). Wait 60 seconds. If this happens often, two fixes:

1. **Add retries** — LiteLLM has built-in retry/backoff. Set `RETRY_ENABLED=true` in `.env`.
2. **Stack a second free provider** — Groq for fast tool calls, Gemini for synthesis. See `APPENDIX-OLLAMA.md` for hybrid configs.

### `403 PERMISSION_DENIED`
The Generative Language API isn't enabled on your Google Cloud project. Easiest fix: create a fresh API key from AI Studio (separate from any Cloud project) and use that.

### CrewAI installation fails with `tiktoken` build error
You need build tools. Mac: `xcode-select --install`. Linux: `apt install build-essential python3-dev`.

### `Model not found`
Model strings for LiteLLM use the prefix format `gemini/gemini-2.5-flash`. Not `gemini-2.5-flash`, not `google/gemini`. Always `gemini/<model-name>`.

### Slow first response (5–10s)
Normal — Gemini's first call after idle has cold-start latency. Subsequent calls within the same session are ~1–2s.

### "Region not supported"
Free tier requires the API to be available in your region. As of 2026 it works in India and most countries. If blocked, use a VPN to set up the key, then use normally.

### Want to use Anthropic Claude / OpenAI instead
Set the relevant key in `.env` (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`) and change `MAIN_MODEL=anthropic/claude-haiku-4-5` or `MAIN_MODEL=gpt-4o-mini`. CrewAI/LiteLLM handles the rest automatically — same code works.

### Want fully local (no cloud, no API key)
See [`APPENDIX-OLLAMA.md`](./APPENDIX-OLLAMA.md). Install Ollama, change two `.env` values, done.

---

## Next step

→ Continue to [`02-week1-tool-calling.md`](./02-week1-tool-calling.md).
