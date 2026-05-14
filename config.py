"""
Centralized configuration and LLM factory.

Why this file exists: in Week 7 you'll add model tiering (cheap model for routing,
bigger model for synthesis). Having one place that produces LLM instances means
you change tiers without touching agents.

Default stack: Google Gemini (free AI Studio tier).
Fallback: Ollama (fully local) — see docs/APPENDIX-OLLAMA.md.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root regardless of where the script is invoked from
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")


# ---------- Env -----------------------------------------------------------

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
MAIN_MODEL = os.getenv("MAIN_MODEL", "gemini/gemini-2.5-flash")
ROUTER_MODEL = os.getenv("ROUTER_MODEL", "gemini/gemini-2.5-flash-lite")
EMBED_MODEL = os.getenv("EMBED_MODEL", "models/text-embedding-004")
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/multi_agent_system",
)

# For Ollama fallback (only used if MAIN_MODEL starts with "ollama/")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Detect provider from MAIN_MODEL prefix
USING_OLLAMA = MAIN_MODEL.startswith("ollama/")


# ---------- Sanity check on import ----------------------------------------

if not USING_OLLAMA and not GOOGLE_API_KEY:
    raise RuntimeError(
        "GOOGLE_API_KEY is missing from .env. "
        "Get a free key at https://aistudio.google.com/apikey, "
        "or set MAIN_MODEL=ollama/... for fully local mode "
        "(see docs/APPENDIX-OLLAMA.md)."
    )

# LiteLLM reads GEMINI_API_KEY by convention; mirror it from GOOGLE_API_KEY
if GOOGLE_API_KEY:
    os.environ.setdefault("GEMINI_API_KEY", GOOGLE_API_KEY)


# ---------- LLM factory ---------------------------------------------------

def make_crewai_llm(tier: str = "main"):
    """Return a CrewAI LLM instance.

    tier: "main" for reasoning, "router" for cheap classification.
    """
    from crewai import LLM

    model = MAIN_MODEL if tier == "main" else ROUTER_MODEL

    kwargs = {
        "model": model,
        "temperature": 0.2,
    }
    # Ollama needs the base_url; hosted providers infer endpoint from prefix
    if model.startswith("ollama/"):
        kwargs["base_url"] = OLLAMA_BASE_URL

    return LLM(**kwargs)


# ---------- Embeddings ----------------------------------------------------

@lru_cache(maxsize=1)
def get_embeddings():
    """Return a langchain Embeddings instance. Cached so we instantiate once."""
    if USING_OLLAMA:
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(
            model=EMBED_MODEL,
            base_url=OLLAMA_BASE_URL,
        )

    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    return GoogleGenerativeAIEmbeddings(
        model=EMBED_MODEL,
        google_api_key=GOOGLE_API_KEY,
    )


# ---------- LangChain/LangGraph LLM (Week 5+) -----------------------------

def make_langchain_llm(tier: str = "main"):
    """Return a langchain ChatModel (used by LangGraph nodes)."""
    model = MAIN_MODEL if tier == "main" else ROUTER_MODEL

    if model.startswith("ollama/"):
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=model.removeprefix("ollama/"),
            base_url=OLLAMA_BASE_URL,
            temperature=0.2,
        )

    # Default: Gemini
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model=model.removeprefix("gemini/"),
        google_api_key=GOOGLE_API_KEY,
        temperature=0.2,
    )
