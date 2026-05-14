# Week 6 — Evaluation

**Goal:** Measure your system. Build a golden set, run Ragas, hit production-grade scores. Without this step the project looks amateur — with it, it looks senior.

**Time:** 6–8 hours.

**You'll touch:** `src/evals/ragas_eval.py`, `src/evals/golden_set.json`.

---

## Why evals matter more than you think

Every RAG system looks fine on the 3 questions the developer tested. Every RAG system has wildly different quality across questions you didn't test. **Evals are the only way to know which one you actually built.**

The dirty secret: most "production" AI systems in 2024–2025 had no automated evals. By 2026 this is changing fast, and companies hire specifically for the skill. Doing this right separates you from the pack.

## The four metrics that matter (Ragas)

| Metric              | What it asks                                                | Production target |
| ------------------- | ----------------------------------------------------------- | ----------------- |
| **Faithfulness**    | Are answer claims supported by the retrieved context?       | ≥ 0.90            |
| **Answer relevancy** | Does the answer actually address the question?             | ≥ 0.85            |
| **Context precision** | Are retrieved chunks ranked by relevance (top = best)?    | ≥ 0.80            |
| **Context recall**  | Did retrieval find all the info needed to answer?           | ≥ 0.80            |

Faithfulness measures **hallucination** — claims with no source support. Production-blocking if low.

Answer relevancy catches **off-topic answers** — the LLM ramble.

Context precision/recall measure **retrieval quality** — independent of the LLM.

These four cover most failure modes. Track them all.

## Concept: the golden set

A **golden set** is a small (30–50 question) curated dataset:

```json
[
  {
    "question": "What is the standard chunk overlap percentage for RAG?",
    "ground_truth": "10–20% overlap is the common recommendation to preserve context at chunk boundaries.",
    "expected_arxiv_ids": ["2310.11511", "2404.10981"]
  },
  ...
]
```

Each entry has:
- A real question users would ask
- A ground-truth answer (you write it, citing real papers)
- Expected sources (optional but useful)

**You write the golden set yourself.** Yes, it's tedious. Yes, it's the most important file in the project. Spend 4 hours on this. Cover:
- Easy / medium / hard questions
- In-corpus / partly-in-corpus / out-of-corpus
- Specific / broad / comparative

## The eval loop

```python
# src/evals/ragas_eval.py
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from datasets import Dataset

# 1. Run your system on every golden question, capture answer + retrieved chunks
records = []
for q in golden_set:
    result = workflow.invoke({"question": q["question"], "iterations": 0})
    records.append({
        "question": q["question"],
        "answer": result["final_report"],
        "contexts": [c["content"] for c in result["chunks"]],
        "ground_truth": q["ground_truth"],
    })

# 2. Ragas evaluates
dataset = Dataset.from_list(records)
scores = evaluate(dataset, metrics=[
    faithfulness, answer_relevancy, context_precision, context_recall
])
print(scores)
```

That's the entire eval pipeline. ~30 lines.

## The iteration loop

1. Run evals. Get baseline scores.
2. Look at the **worst 5 questions**. Read what went wrong.
3. Make ONE change. (Bigger chunks? Add reranker? Improve writer prompt?)
4. Re-run evals. Did it help?
5. Repeat.

Without this loop you're guessing. With it, you optimize.

## Concept: Langfuse tracing

Ragas tells you **what** is broken. Langfuse tells you **where**.

Langfuse hooks into your LLM calls and tool calls automatically, producing a per-run trace:

```
[Run 7d8f...]
├── plan_node            420ms   $0.00 (local)
├── retrieve_node       1820ms   vector_search top_k=5
│   └── chunks: 5 (avg score 0.78)
├── research_node       4200ms
│   ├── arxiv_search(query="...")    1900ms
│   └── arxiv_search(query="...")    2100ms
├── fact_check_node     2100ms
│   └── grounded=False, retry=1
├── research_node        ...        (loop!)
└── write_node          3800ms
```

You can see every prompt, every output, every latency. Filter by score. Find traces where faithfulness was low and see what the retrieval looked like.

Setup (Langfuse cloud has a free tier):
```python
from langfuse.langchain import CallbackHandler
handler = CallbackHandler()

# pass into your llm calls:
llm.invoke(prompt, config={"callbacks": [handler]})
```

For LangGraph it's even simpler — pass the callback in `config` and every node gets traced.

## Step 1 — Build the golden set

Block out 3–4 hours. Open `src/evals/golden_set.json`. Write 30 questions across the difficulty spectrum. Mix:
- "What is X?" (factual)
- "Compare X and Y." (comparative)
- "Why does X happen?" (causal)
- "Recent advances in X" (recall-heavy)
- "Critique X." (judgment)

For each, write the ground truth answer in 1–3 sentences. Cite arXiv IDs you've ingested.

## Step 2 — Wire up the eval pipeline

Write `src/evals/ragas_eval.py`. Run:

```bash
python -m src.evals.ragas_eval
```

Expect 10–20 minutes — Ragas calls the LLM-as-judge several times per question. Save results to `evals/results_<date>.json`.

## Step 3 — Wire up Langfuse

Sign up at <https://cloud.langfuse.com> (free). Add keys to `.env`. Re-run a single test query — verify the trace appears in the dashboard.

## Step 4 — Set up the iteration loop

For each change you make to chunking, retrieval, prompts:
1. Tag the run (`run_name="chunk_size_400"`)
2. Compare scores side-by-side
3. Keep changes that improve. Revert changes that don't.

## Checkpoint

Done with Week 6 when:

- [ ] Golden set has ≥30 questions, all with ground truths
- [ ] Eval pipeline runs end-to-end
- [ ] Baseline scores recorded
- [ ] You made ≥3 improvements and showed score gains on each
- [ ] Faithfulness ≥0.85, answer relevancy ≥0.80, context precision ≥0.75
- [ ] Langfuse shows traces for every eval run
- [ ] You can identify your worst-performing question and explain why

## Things to try

1. **A/B chunk sizes.** Run evals with chunk=400 vs 800 vs 1600. Pick the winner.
2. **Add a reranker.** Drop bge-reranker-v2-m3 in front of the LLM. Re-run. Faithfulness should jump.
3. **Improve the writer prompt.** Add: "Cite arXiv IDs inline. Only make claims supported by the provided context. If unsupported, write 'Evidence is limited.'" Re-evaluate.
4. **Tighten retrieval to top-3 instead of top-10.** Less context, more precision. See what happens.

## Common pitfalls

**Ragas is slow.** It uses an LLM-as-judge for each metric. Use a cheap-but-capable model (`gemini-2.5-flash-lite`, `gpt-4o-mini`, or local `llama3.1:70b`) — not your main model.

**Golden set is too easy.** All questions answerable from training data → high relevancy but useless signal. Include hard, niche questions only your corpus can answer.

**Scores plateau.** You hit your retrieval ceiling. Try contextual embeddings (Anthropic's contextual retrieval) or BM25 + vector hybrid.

**Faithfulness low even with good retrieval.** The Writer is hallucinating. Add a constraint in the prompt and a fact-check node (already in Week 5).

**Langfuse traces empty.** Callbacks not attached to all LLM calls. Pass via `config={"callbacks": [...]}` on every `.invoke()` and every LangGraph compile.

## Reading

- Ragas docs (read the metrics page fully): <https://docs.ragas.io/en/latest/concepts/metrics/index.html>
- Langfuse Python docs: <https://langfuse.com/docs/sdk/python>
- "Evaluating RAG" (good overview): <https://www.pinecone.io/learn/series/vector-databases-in-production-for-busy-engineers/rag-evaluation/>

## Next step

→ Continue to [`08-week7-optimization.md`](./08-week7-optimization.md).
