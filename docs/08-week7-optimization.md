# Week 7 — Cost & Latency Optimization

**Goal:** Make the system faster and cheaper without losing quality. Implement model tiering, caching, and prompt optimization. Track cost per *task*, not per token.

**Time:** 4–6 hours.

**You'll touch:** `src/config.py`, all node functions, `.env`.

---

## The mental shift: cost-per-task

Token costs are a distraction. The user doesn't pay for tokens — they pay for **outcomes**: a resolved ticket, a research report, a code review.

The metric you actually care about:

```
cost per completed task = sum(tokens × $per_token) per successful run
```

A workflow that uses 50K tokens but gets it right first try beats one that uses 20K and loops 3 times.

Latency works the same way: **time to acceptable answer**, not time-to-first-token.

## Lever 1 — Model tiering

Not every step needs your strongest model. Route by task:

| Task                         | Model                          | Why                              |
| ---------------------------- | ------------------------------ | -------------------------------- |
| Query classification         | `gemini-2.5-flash-lite`        | Smallest, fastest, free          |
| Sub-question decomposition   | `gemini-2.5-flash-lite`        | Easy task, save Flash quota      |
| Tool argument generation     | `gemini-2.5-flash`             | Tool calling needs more capacity |
| Retrieval evaluation         | `gemini-2.5-flash-lite`        | Yes/no classification            |
| Final synthesis              | `gemini-2.5-flash` (or Pro)    | The output the user sees         |
| Fact-check                   | `gemini-2.5-flash`             | Needs reasoning over chunks      |

Implementation: your `make_llm("main" | "router")` factory already supports this. The router tier uses Flash-Lite; main uses Flash.

**In practice:** ~70% of LLM calls in a multi-agent system are routing/classification — those can run on the cheaper Flash-Lite tier. This both reduces token spend (if you ever go paid) AND helps you stay under the per-minute rate limit by spreading load across two models.

## Lever 2 — Prompt compression

Big prompts = slow + expensive. Audit each agent's prompt:

- **Backstory bloat** — does each sentence change behavior? If not, cut it.
- **Few-shot examples** — keep 1–2 per agent. More rarely helps; it just costs tokens.
- **Truncate tool output** — your `arxiv_search` returns 5 papers with full abstracts (500 words each). 2500 words → ~1700 tokens of context. Truncate abstracts to 300 chars for routing decisions; full text only when needed.

Target: cut average input tokens per run by 40% with no quality loss. Measure with Langfuse before/after.

## Lever 3 — Caching

Two layers:

**Embedding cache.** A query embedded twice = wasted compute. Hash query → embedding. SQLite or Redis. Add an `@lru_cache(maxsize=10000)` wrapper.

**LLM response cache.** Same prompt + same model + temp=0 = same answer. LangChain has built-in caching:

```python
from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

set_llm_cache(SQLiteCache(database_path=".llm_cache.db"))
```

Caching matters less during dev (you ask different questions) but a lot in prod (similar queries repeat).

## Lever 4 — Parallel execution

Where possible, run nodes concurrently. In LangGraph:

```python
graph.add_edge("plan", "retrieve")   # both run...
graph.add_edge("plan", "research")   # ...in parallel
```

Both fire when `plan` finishes. If retrieve takes 2s and research takes 5s, total = 5s, not 7s.

For multiple sub-questions, use the Send API:

```python
from langgraph.types import Send

def fan_out(state):
    return [Send("research_one", {"sub_q": q}) for q in state["sub_questions"]]
```

5 sub-questions → 5 parallel researcher invocations → results merge via reducer. Latency = max, not sum.

## Lever 5 — Batched embeddings

The `embed_documents()` method on `GoogleGenerativeAIEmbeddings` batches automatically. For ingestion:

```python
# slow — one call per chunk
for chunk in chunks:
    emb = embeddings.embed_query(chunk)

# fast — single batched call
embs = embeddings.embed_documents([c for c in chunks])
```

100 chunks: ~30 seconds vs ~3 seconds. Google's embedding API also has a higher rate limit than the generation API, so batching here rarely trips rate limits.

## Lever 6 — Streaming

Streaming doesn't reduce cost. It reduces **perceived** latency. The user sees output appear word-by-word instead of waiting 10 seconds for a complete answer.

LangGraph supports streaming at node level:

```python
for event in app.stream(input, stream_mode="values"):
    yield event   # ship to frontend via SSE
```

Frontend renders progressively. UX night-and-day better.

## Concept: budget enforcement

Set a budget per query:

```python
class Budget(TypedDict):
    max_iterations: int
    max_tool_calls: int
    max_tokens: int

def check_budget(state):
    if state["iterations"] >= state["budget"]["max_iterations"]:
        return "force_finalize"
    return "continue"
```

Without budgets, agents loop forever on hard questions. Caps force graceful degradation.

## Step-by-step

1. **Measure baseline.** Run 5 questions through your Week 6 system. Record:
   - Total time per question
   - Token usage (sum input + output)
   - Tool call counts
   - Success rate (faithfulness ≥ 0.85)

2. **Add a router model.** In `src/config.py`, plumb the `tier="router"` LLM into:
   - Planner (decomposition is easy)
   - Fact-check pre-filter (yes/no classification)

3. **Cache embeddings.** Wrap `embeddings.embed_query` with `lru_cache`.

4. **Truncate tool outputs.** Cut `arxiv_search` abstract length to 300 chars by default; add a `full_text=False` arg for when you want the long version.

5. **Parallelize retrieve + research in LangGraph.**

6. **Re-measure.** Compare new numbers to baseline. Aim for 30–50% latency reduction and 30%+ token reduction with no eval score regression.

7. **Re-run Week 6 evals.** Verify no quality regressions.

## Checkpoint

Done with Week 7 when:

- [ ] Model tiering is wired in and a fast model handles routing
- [ ] Total tokens per query down ≥30%
- [ ] Wall-clock latency per query down ≥30%
- [ ] Faithfulness still ≥0.85 (no regression!)
- [ ] Streaming works for at least the writer node
- [ ] You have before/after numbers in a markdown table in the project README

## Things to try

1. **Speculative routing.** Run a cheap-model first answer in parallel with the full pipeline. If the cheap answer is acceptable, return it early.
2. **Adaptive top_k.** Easy questions: top_k=3. Hard questions: top_k=10. Classifier decides.
3. **Per-question budget.** Hard cap LLM calls per query (e.g. 20). If exceeded, force-finalize. Prevents one bad question from eating your daily quota.

## Common pitfalls

**Routing the wrong tasks to the small model.** If your sub-question quality drops, the small model can't decompose well. Move that step back up.

**Cache hit rate is 0%.** Your queries are too varied or you forgot the `temperature=0` (caching keys include temp).

**Parallel nodes deadlock.** Two nodes both wait on each other. LangGraph will detect — read the error carefully.

**You optimize the wrong thing.** Always measure first. Don't tier-down a model that wasn't the bottleneck.

## Reading

- Langfuse cost tracking: <https://langfuse.com/docs/model-usage-and-cost>
- LangChain caching: <https://python.langchain.com/docs/integrations/llm_caching/>
- "Multi-agent cost optimization patterns": good search query, several recent posts

## Next step

→ Continue to [`09-week8-ship.md`](./09-week8-ship.md).
