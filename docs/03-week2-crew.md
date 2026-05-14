# Week 2 — Multi-Agent Crew

**Goal:** Build a 3-agent crew (Planner → Researcher → Writer). See why role specialization beats one big prompt — and where it starts to break.

**Time:** 6–8 hours.

**You'll touch:** `src/agents/crew.py`, `scripts/run_week2.py`.

---

## Concept: why split into multiple agents?

A single LLM call with a 2000-word system prompt can technically "plan, research, and write." But three problems emerge:

1. **Context bloat** — all instructions, all tools, all examples in one prompt. The model gets confused about what to do *now*.
2. **No specialization** — the model can't deeply optimize for one role. A Planner needs to be decisive; a Writer needs to be careful. Same prompt = neither.
3. **No checkpoints** — you can't intervene between phases. If planning was bad, the whole thing is bad and you can't tell which step broke.

Multi-agent fixes all three. Each agent has a focused prompt (its role + goal + backstory), its own tools, and produces a discrete artifact (its task output).

## Concept: role, goal, backstory

CrewAI's three fields — they all become parts of the system prompt:

| Field        | What it sets                                  | Example                                              |
| ------------ | --------------------------------------------- | ---------------------------------------------------- |
| `role`       | Identity — short noun phrase                  | `"Academic Researcher"`                              |
| `goal`       | Success criterion — what done looks like      | `"Find recent papers and extract findings."`         |
| `backstory`  | Personality + constraints                     | `"You prefer recent papers, cite arXiv IDs..."`      |

Backstory is where you encode anti-patterns: "you never invent citations," "you say 'I don't know' if evidence is thin." The model takes these seriously.

## Concept: tasks and `expected_output`

```python
task = Task(
    description="Decompose this question into 3-5 sub-questions...",
    expected_output="A numbered list of 3-5 sub-questions with 1-sentence notes.",
    agent=planner,
)
```

The `expected_output` is **the most important field on a task.** It tells the agent what "done" looks like. Without it, the model rambles or stops early.

Treat it like a contract: if you could grade the output against this single sentence, the agent did the job.

## Concept: process types

```python
Crew(..., process=Process.sequential)   # planner → researcher → writer
Crew(..., process=Process.hierarchical) # a manager LLM delegates dynamically
```

Sequential is what you want 90% of the time. Hierarchical adds an extra LLM call per delegation (expensive) and is harder to debug. Start sequential, go hierarchical only when you genuinely need dynamic routing — and by then you'll probably want LangGraph anyway.

## Walkthrough: `src/agents/crew.py`

Open the file. Notice the structure:

1. **Three agents** with non-overlapping roles
2. **Three tasks**, each `context=[previous_task]` — that's how data flows
3. **One crew** running sequentially

Two design decisions worth questioning:

**Why `allow_delegation=False` on the Planner?** Because delegation in CrewAI means *the agent can spawn other agents mid-task*. The Planner's job is just to plan. Giving it delegation rights would let it skip ahead to research, defeating the point.

**Why `tools=[arxiv_tool]` only on the Researcher?** Tool access should be minimal. The Planner doesn't need to search; the Writer doesn't either. Restricting tools is both safer and faster.

## Run it

```bash
python scripts/run_week2.py "Compare LoRA vs full fine-tuning for LLMs"
```

Watch all three agents run. Read each task's output carefully.

## What the output reveals

You'll notice:

✅ **The plan is usually decent.** Llama 3.1 handles decomposition fine.

⚠️ **The research is hit-or-miss.** The Researcher does 1–2 searches per sub-question. Sometimes it picks bad queries.

⚠️ **The writer hallucinates citations occasionally** — it'll cite a paper by ID that wasn't in the research output. **This is the central problem RAG and a fact-checker solve.** You will fix this in Weeks 3 and 5.

This is exactly the pain point you're supposed to feel.

## Checkpoint

Done with Week 2 when:

- [ ] The 3-agent crew runs to completion.
- [ ] The final report has at least 3 cited arXiv IDs.
- [ ] You ran 5 different questions and noted how output quality varies.
- [ ] You can name **two ways** this system is worse than a single Claude/GPT-4 call.
- [ ] You can name **three ways** it's better (or could be).

## Things to try

1. **Make the Planner worse on purpose** — change `goal` to `"Plan something."`. Re-run. How bad does the cascade get?
2. **Remove the Researcher's tool** — what does it do?
3. **Add a 4th agent** — a "Skeptic" that critiques the Writer's draft. Does it improve quality? Does it slow things down?
4. **Run the same question 3 times.** Are the outputs consistent? (Spoiler: no — this is why temperature matters.)

## Common pitfalls

**Agents repeat each other's work.** Means their roles overlap. Tighten the goals.

**The Writer ignores the Researcher's output.** Usually because the Researcher's output was too long and got truncated. Add a constraint to the Researcher's `expected_output`: "Max 800 words total."

**Crew runs but final output is empty.** Almost always `max_iter` was hit silently. Bump to 10 temporarily to diagnose.

**Hallucinated citations.** Real problem, real solution coming in Week 3. For now, note them.

## Reading

- CrewAI core concepts: <https://docs.crewai.com/concepts/agents>, <https://docs.crewai.com/concepts/tasks>
- CrewAI examples (read 2–3 fully): <https://github.com/crewAIInc/crewAI/tree/main/examples>

## Next step

→ Continue to [`04-week3-rag.md`](./04-week3-rag.md). This is the biggest week. Block out time.
