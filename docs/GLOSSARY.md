# Glossary

Quick definitions of every term you'll encounter in this project. Use this when something feels vague.

---

**Agent.** An LLM-driven process that can decide to call tools, read results, and produce outputs. Distinct from a plain LLM call because it loops: reason → act → observe → reason.

**Agentic RAG.** RAG where the agent decides whether to retrieve, how to query, whether to retry. Contrast with plain RAG, which is a single retrieve-then-generate pipeline.

**A2A (Agent-to-Agent protocol).** Standard for agents from *different frameworks* to discover and communicate with each other. Google introduced it; widely adopted in 2025–2026.

**Backstory.** In CrewAI, a free-form personality + constraints field for an agent. Becomes part of the system prompt.

**Backend.** Server-side code. In this project, the FastAPI service in Week 8.

**Chunk.** A piece of a document, typically 200–800 tokens, used as the unit of retrieval in RAG.

**Chunking.** The process of splitting documents into chunks. Quality of chunking is the single biggest lever for RAG quality.

**Citation.** A reference in agent output to the source it came from. In this project, arXiv IDs like `[arXiv:2501.12345]`.

**Conditional edge.** In LangGraph, a function `state → next_node_name` that determines branching. The mechanism that enables loops and branches.

**Context.** (1) The text the LLM sees in its prompt. (2) The dependency relationship between tasks in CrewAI: `task_b.context=[task_a]` means b reads a's output.

**Context precision.** Ragas metric. Of the retrieved chunks, are the most relevant ones ranked highest? Production target ≥ 0.80.

**Context recall.** Ragas metric. Did retrieval find all the chunks needed to answer? Production target ≥ 0.80.

**Crew.** In CrewAI, a collection of agents + tasks + a process (sequential/hierarchical) that runs together.

**Embedding.** A vector representation of text where similar text → similar vectors. `nomic-embed-text` produces 768-dim embeddings.

**Eval (evaluation).** Automated quality measurement on a fixed test set. The thing that separates "looks fine on my 3 questions" from a system you can trust.

**Faithfulness.** Ragas metric. Are the answer's claims actually supported by the retrieved context? Production target ≥ 0.90. Low faithfulness = hallucination.

**FastAPI.** Python async web framework used to expose your agent as an HTTP service.

**Few-shot.** Including 1–5 example input/output pairs in the prompt to teach the model the desired format. Often unnecessary with modern LLMs; cuts cost when dropped.

**Frontend.** Client-side UI. In Week 8: Streamlit, Next.js, or plain HTML.

**Golden set.** A small (30–50) curated dataset of questions + ground-truth answers used to evaluate the system over time.

**Ground truth.** The correct answer for a benchmark question, used to score model outputs.

**Hallucination.** When the LLM produces a confident statement not supported by evidence. The central problem RAG and fact-checkers solve.

**Hybrid search.** Combining vector similarity (semantic) with BM25 (keyword) search. Better recall than either alone.

**IVFFlat.** A pgvector index type that partitions vectors into clusters for fast approximate search. Set `lists ≈ sqrt(N rows)`.

**Langfuse.** Observability platform. Traces every LLM call, tool call, and node execution. Free tier available.

**LangGraph.** LangChain's graph-based agent orchestration framework. Nodes are functions, edges define flow, state passes between them. Production standard in 2026.

**LiteLLM.** A library that translates between many LLM providers' APIs to a single OpenAI-compatible interface. CrewAI uses it internally.

**LLM-as-judge.** Using one LLM to score the output of another. Ragas uses this for several of its metrics.

**MCP (Model Context Protocol).** Open standard for connecting agents to tools, data, and prompts. Donated to Linux Foundation in Dec 2025. Adopted by Anthropic, OpenAI, Google.

**MCP server.** A process that exposes tools/resources/prompts via the MCP protocol. You build one in Week 4.

**MCP client.** Anything that consumes an MCP server. Claude Desktop, Cursor, your CrewAI crew, future agents.

**MMR (Maximal Marginal Relevance).** Retrieval technique that picks chunks balancing relevance to query and diversity from each other. Avoids "top-5 are all from the same paper."

**Multi-agent system.** A system of multiple specialized agents that coordinate to solve a task no single agent could solve well.

**Node.** In LangGraph, a function in the graph that reads state and returns updates.

**Ollama.** A local LLM runner. Pull models, run them, get an OpenAI-compatible API on `localhost:11434`.

**Orchestration.** The "who does what, when, and how data flows" layer. CrewAI does it implicitly (sequential/hierarchical); LangGraph does it explicitly (you draw the graph).

**Overlap.** In chunking, the number of characters/tokens shared between adjacent chunks. 10–20% is standard; preserves context at boundaries.

**pgvector.** A Postgres extension that adds a `vector` type and similarity search operators. Lets you use familiar SQL for vector workloads.

**Pinecone.** Managed vector database. Easiest hosted option. Alternative to pgvector.

**Planner.** An agent role specializing in decomposing a complex question into sub-questions. The first agent in our crew.

**Prompt (MCP).** A reusable prompt template exposed by an MCP server. Appears as a slash command in MCP clients like Claude Desktop.

**Process.** In CrewAI: `Process.sequential` or `Process.hierarchical`. Controls how agents are scheduled.

**Pydantic.** Python library for typed data validation. Used to define tool argument schemas that agents see as JSON schema.

**Ragas.** Evaluation library for RAG and agentic systems. Faithfulness, answer relevancy, context precision/recall are the core metrics.

**ReAct.** Reasoning + Acting. The interleaved-thought-and-action pattern foundational to every agent framework. From the [original paper](https://arxiv.org/abs/2210.03629).

**Reducer.** In LangGraph, the function that decides how to merge updates to a state field. `Annotated[list, add]` makes a field append-only.

**Reranker.** A model that re-orders retrieved chunks for relevance. Slower per pair than embedding similarity, more precise. `bge-reranker-v2-m3` and Cohere Rerank are standard.

**Resource (MCP).** A piece of data (file, URL) an MCP server exposes. Clients can reference it (e.g. `@-mention` in Claude Desktop).

**Retrieval.** The "R" in RAG. The process of finding relevant chunks from a vector DB given a query.

**Role.** An agent's identity. In CrewAI, a short noun phrase like `"Academic Researcher"`.

**Semantic chunking.** Chunking that uses embedding distance between sentences to find semantic boundaries. Best-quality chunking method.

**Sequential process.** CrewAI execution mode where tasks run one after another in a fixed order. The default; use unless you need branching.

**SSE (Server-Sent Events).** A simple streaming protocol over HTTP. One-way: server → client. Used in Week 8 to stream agent progress to the UI.

**State.** In LangGraph, the typed dictionary that flows through the graph and is updated by nodes.

**Streaming.** Sending output progressively rather than waiting for the full response. Reduces *perceived* latency.

**System prompt.** The initial instructions given to an LLM that establish role, behavior, constraints. In CrewAI, role + goal + backstory together compose the system prompt.

**Task.** In CrewAI, a unit of work assigned to an agent, with a description and `expected_output`.

**Tool.** A function the agent can call. Defined with a name, description, and typed args.

**Tool calling.** The mechanism by which an LLM emits a structured request for a tool to be executed. The LLM names the tool and args; the runner executes.

**Top-K.** The number of chunks returned by similarity search. Typical values: 3–10 for the LLM context; 20+ if a reranker will narrow further.

**Vector.** An ordered list of N numbers (here, 768 numbers). The numerical representation of meaning.

**Vector DB.** A database optimized for storing and similarity-searching vectors. Examples: pgvector, Pinecone, Weaviate, Qdrant, Chroma.

**Vector search.** Finding the K vectors closest to a query vector, by cosine or Euclidean distance.

---

→ Back to [`README.md`](../README.md).
