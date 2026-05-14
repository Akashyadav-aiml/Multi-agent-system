# Appendix — Run Fully Local with Ollama

If you want zero cloud dependencies (offline, air-gapped, or just paranoid about data leaving your machine), you can swap Gemini for Ollama. The rest of the project — CrewAI, LangGraph, pgvector, MCP, Ragas — is unchanged.

## When to choose Ollama

- You want everything 100% local with no API key
- You have a strong laptop (≥16 GB RAM, ideally a GPU)
- You don't mind weaker tool calling vs frontier-class hosted models
- Privacy/compliance requires no data to leave your machine

## When NOT to choose Ollama

- You have a low-spec laptop — 8B models will be slow and frustrating
- You want the best possible output quality — open 8B–13B models are noticeably weaker at multi-step reasoning than Gemini 2.5 Flash
- You're shipping to recruiters in Week 8 — hosted models look more professional in demos

## Setup

### 1. Install Ollama

Get it from <https://ollama.com>. Then in a terminal:

```bash
ollama serve   # leave this running
```

In another terminal, pull the models:

```bash
ollama pull llama3.1:8b           # ~4.7 GB — main reasoning model
ollama pull qwen2.5:3b            # ~2 GB — cheap router model (Week 7)
ollama pull nomic-embed-text      # ~280 MB — 768-dim embeddings
```

**Verify:**

```bash
curl http://localhost:11434/api/tags
ollama run llama3.1:8b "What's 2+2? One sentence."
```

### 2. Change `.env`

Comment out the Gemini block and use these instead:

```bash
# --- Ollama (local, no API key needed) ---
OLLAMA_BASE_URL=http://localhost:11434
MAIN_MODEL=ollama/llama3.1:8b
ROUTER_MODEL=ollama/qwen2.5:3b
EMBED_MODEL=nomic-embed-text
EMBED_DIM=768

# Leave GOOGLE_API_KEY blank (or remove the line)
GOOGLE_API_KEY=
```

### 3. Change `src/config.py`

Add an Ollama branch to the LLM factory:

```python
def make_crewai_llm(tier: str = "main"):
    from crewai import LLM
    model = os.getenv("MAIN_MODEL" if tier == "main" else "ROUTER_MODEL")

    # Ollama needs base_url; hosted providers don't
    base_url = os.getenv("OLLAMA_BASE_URL") if model.startswith("ollama/") else None

    return LLM(
        model=model,
        base_url=base_url,
        temperature=0.2,
    )
```

For embeddings, swap `GoogleGenerativeAIEmbeddings` for `OllamaEmbeddings`:

```python
@lru_cache(maxsize=1)
def get_embeddings():
    if os.getenv("GOOGLE_API_KEY"):
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    else:
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(
            model=os.getenv("EMBED_MODEL", "nomic-embed-text"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
```

### 4. Install Ollama Python packages

```bash
pip install langchain-ollama
```

Now everything runs locally.

## Hybrid setup (best of both worlds)

You can mix providers — use Gemini for synthesis (better quality) and Ollama for routing (free, no rate limit):

```bash
GOOGLE_API_KEY=AIza...
MAIN_MODEL=gemini/gemini-2.5-flash       # smart, hosted, rate-limited
ROUTER_MODEL=ollama/qwen2.5:3b            # cheap, local, unlimited
EMBED_MODEL=nomic-embed-text              # free local embeddings
```

This sidesteps the Gemini per-minute rate limit on classification steps while keeping the strong model for synthesis. It's actually a common production pattern — route cheap tasks to cheap models.

## Tradeoffs you'll feel

**Llama 3.1 8B vs Gemini 2.5 Flash for tool calling:**
- Llama sometimes skips tool calls on questions it thinks it can answer
- Llama is more sensitive to bad tool descriptions
- Llama loops more — set `max_iter` lower (3–5)
- Quality of final reports is ~15–25% worse on subjective evals

**Speed:**
- First request: Ollama loads the model (5–15s). Gemini cold-start ~5s.
- Subsequent: Ollama 2–10s/call (depends on hardware). Gemini 1–3s/call.

**Rate limits:**
- Ollama: none. Run as much as you want.
- Gemini free tier: ~10–15 RPM, 1,500 req/day.

For learning, Ollama's "no limits" is actually nice — you can iterate fast without worrying about quota.

## My recommendation

**Start with Gemini.** Get the project working with the better model first. You'll learn the patterns without fighting model weakness. Switch to Ollama later if you want the local-only credential, or use the hybrid setup above.

If you absolutely must go local from day one — fine, the project still works. Just expect to spend more time debugging agent loops and tweaking prompts.

---

→ Back to [`README.md`](../README.md).
