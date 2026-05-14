# Week 1 — Tool Calling

**Goal:** Get tool calling working end-to-end with one agent and one tool. Feel how the LLM decides when to call the tool, then read the result and respond.

**Time:** 4–6 hours.

**You'll touch:** `src/tools/arxiv_search.py`, `scripts/run_week1.py`.

---

## Concept: what is tool calling, really?

Tool calling is **the LLM emitting a structured request for a function to be executed, instead of (or in addition to) plain text**. The orchestrator (CrewAI, here) intercepts that request, runs the function, and feeds the result back into the next LLM call.

The flow:

```
User:    "What's hot in transformer research?"
   ↓
LLM:     thinks → emits { "tool": "arxiv_search", "args": {"query": "transformer 2025"} }
   ↓
Runner:  executes arxiv_search("transformer 2025") → returns paper list
   ↓
LLM:     reads results → emits final text answer with citations
```

Critically: **the LLM never runs the tool itself.** It just *names* the tool and supplies arguments. Your code runs the function. This separation is what makes agents safe — you control what tools exist and what they can do.

## Concept: tool description = the most important prompt

The LLM picks tools based on **two pieces of text**:

1. The tool's `name`
2. The tool's `description`

That's it. The model never sees your Python code. So those two fields are not docstrings — they're prompts. Bad description → tool gets ignored or misused.

Compare:

❌ Bad: `"Searches arXiv for papers."` (vague — when should the LLM use this vs answer from memory?)

✅ Good: `"Search arXiv for recent academic papers. Use this when the user asks about research, methods, benchmarks, or wants citations from primary sources. Returns titles, authors, abstracts, and arXiv IDs."`

The "Use this when..." is doing real work.

## Concept: typed arguments via Pydantic

CrewAI (and LangChain, and OpenAI's function calling, and MCP) all generate a **JSON schema** from a Pydantic model and hand it to the LLM. The LLM is then constrained to produce arguments matching that schema.

In `src/tools/arxiv_search.py`:

```python
class ArxivSearchInput(BaseModel):
    query: str = Field(..., description="Natural-language search query. Examples: ...")
    max_results: int = Field(default=5, ge=1, le=20)
```

The `description` and `ge`/`le` bounds become part of the schema the LLM sees. Open-source models like Llama 3.1 are sensitive to bad descriptions — invest the time here.

## Walkthrough: `src/tools/arxiv_search.py`

Read the file. Three things to notice:

1. **It inherits `BaseTool`** — CrewAI's contract. Same shape as LangChain's `BaseTool`. MCP is similar but protocol-based.
2. **`_run` is the actual function** — synchronous. For async, override `_arun`.
3. **The return value is a string** — formatted for the LLM to *read*. Not JSON, not Python objects. **Tools always return strings the model can consume directly.** Pre-format, pre-truncate, pre-clean.

## Walkthrough: `scripts/run_week1.py`

```python
researcher = Agent(
    role="Research Assistant",
    goal="Answer the user's research question by finding relevant arXiv papers.",
    backstory="You are a careful research assistant...",
    llm=make_crewai_llm("main"),
    tools=[ArxivSearchTool()],
    verbose=True,
    max_iter=5,
)
```

Four lines that matter:

- `role` — the agent's identity. Acts like the system prompt header.
- `goal` — what success looks like.
- `tools` — Python list of tool instances. The agent decides when to call.
- `max_iter=5` — **safety cap on reasoning loops.** Without this, agents can loop forever. Always set in dev.

## Run it

```bash
python scripts/run_week1.py "What are recent advances in mixture of experts models?"
```

In the verbose output, look for:

```
Thought: I should search arXiv for recent MoE papers.
Action: arxiv_search
Action Input: {"query": "mixture of experts transformer 2025", "max_results": 5}
Observation: Found 5 papers for 'mixture of experts transformer 2025': ...
Thought: I have enough information to answer.
Final Answer: ...
```

That `Thought → Action → Observation → Thought` loop is **ReAct** (Reasoning + Acting). It's the foundation of every agent framework. CrewAI and LangChain both implement it.

## Checkpoint

You're done with Week 1 when you can answer YES to all of these:

- [ ] My agent ran without crashing.
- [ ] I can see the agent call `arxiv_search` in the verbose log.
- [ ] The final answer cites at least one arXiv ID.
- [ ] I tried 5 different questions and watched what the agent did with each.
- [ ] I can explain, in my own words, why the tool description matters more than the function body.

## Things to try (don't skip)

1. **Make the description terrible** — change it to `"Searches papers."`. Re-run. Does the agent still call it? When does it fail?
2. **Add a second tool** — write a `calculator` tool. Ask a question that needs both ("How many papers cited by [X] were published in the last year?"). Watch how the agent chains them.
3. **Lower `max_iter` to 2** — what happens on a complex question?
4. **Force a bad query** — ask something arXiv has no answer for ("What's the weather in Pune?"). Does the agent give up gracefully or loop?

These experiments teach you more than 10 blog posts.

## Common pitfalls

**Llama 3.1 8B sometimes skips the tool on easy questions.** It "knows" the answer from training and answers directly. This is correct behavior! Tool calling is for when the model *needs* fresh/external info. Test with questions that require recent papers (post-2024).

**The agent loops endlessly.** Always set `max_iter`. If you hit the cap repeatedly, your tool description is unclear or the tool is returning useless results.

**Tool returns raw JSON dict and the agent breaks.** Tools must return strings. Format them.

**You see "model not found".** The LiteLLM string format for Ollama is `ollama/<model>`, with the slash. Not `ollama:llama3.1`. Not `llama3.1`. Always `ollama/llama3.1:8b`.

## Reading (do before Week 2)

- LangChain Tools concept: <https://python.langchain.com/docs/concepts/tools/>
- CrewAI Tools guide: <https://docs.crewai.com/concepts/tools>
- The ReAct paper (skim section 2): <https://arxiv.org/abs/2210.03629>

## Next step

→ Continue to [`03-week2-crew.md`](./03-week2-crew.md).
