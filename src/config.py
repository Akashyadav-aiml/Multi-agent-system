"""Centralized configuration and LLM factory.

Why this file exists: in Week 7 you'll add model tiering (cheap model for routing,
bigger model for synthesis). Having one place that produces LLM instances means
you change tiers without touching agents.

Supported model prefixes (works for both CrewAI/LiteLLM and langchain chat models):
    gemini/        — Google Gemini (default, free tier)
    ollama/        — Local Ollama
    anthropic/     — Anthropic Claude
    openai/        — OpenAI GPT
    groq/          — Groq (fast Llama / Mixtral)

Default stack: Gemini. Fallback: Ollama (see docs/APPENDIX-OLLAMA.md).
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

log = logging.getLogger(__name__)


# ---------- Env -----------------------------------------------------------

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

MAIN_MODEL = os.getenv("MAIN_MODEL", "gemini/gemini-2.5-flash")
ROUTER_MODEL = os.getenv("ROUTER_MODEL", "gemini/gemini-2.5-flash-lite")
EMBED_MODEL = os.getenv("EMBED_MODEL", "models/text-embedding-004")
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/multi_agent_system",
)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

SUPPORTED_PREFIXES = ("gemini/", "ollama/", "anthropic/", "openai/", "groq/")


def _provider_of(model: str) -> str:
    for p in SUPPORTED_PREFIXES:
        if model.startswith(p):
            return p.rstrip("/")
    raise RuntimeError(
        f"Unknown model prefix in {model!r}. "
        f"Supported: {', '.join(SUPPORTED_PREFIXES)}"
    )


USING_OLLAMA = MAIN_MODEL.startswith("ollama/")
PROVIDER = _provider_of(MAIN_MODEL)


# ---------- Sanity check on import ----------------------------------------

_KEY_FOR_PROVIDER = {
    "gemini": ("GOOGLE_API_KEY", GOOGLE_API_KEY),
    "anthropic": ("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY),
    "openai": ("OPENAI_API_KEY", OPENAI_API_KEY),
    "groq": ("GROQ_API_KEY", GROQ_API_KEY),
}

# Soft check — let modules import (e.g. for tests/CI), but warn loudly.
if PROVIDER in _KEY_FOR_PROVIDER:
    var_name, value = _KEY_FOR_PROVIDER[PROVIDER]
    if not value:
        log.warning(
            "%s is not set. The default %s provider will fail at first LLM call. "
            "Set it in .env or switch MAIN_MODEL to a provider with credentials.",
            var_name,
            PROVIDER,
        )

# LiteLLM uses GEMINI_API_KEY by convention; mirror it from GOOGLE_API_KEY.
if GOOGLE_API_KEY:
    os.environ.setdefault("GEMINI_API_KEY", GOOGLE_API_KEY)


# ---------- LLM factory: CrewAI (via LiteLLM) -----------------------------

def make_crewai_llm(tier: str = "main"):
    """Return a CrewAI LLM instance.

    LiteLLM natively understands all our supported prefixes, so we mostly just
    pass `model` through; ollama is the only one that needs `base_url`.
    """
    from crewai import LLM

    model = MAIN_MODEL if tier == "main" else ROUTER_MODEL
    provider = _provider_of(model)

    kwargs: dict = {"model": model, "temperature": 0.2}
    if provider == "ollama":
        kwargs["base_url"] = OLLAMA_BASE_URL

    return LLM(**kwargs)


# ---------- LLM factory: LangChain / LangGraph ----------------------------

def make_langchain_llm(tier: str = "main"):
    """Return a langchain ChatModel. Used by LangGraph nodes.

    Attaches Langfuse callbacks if configured (graceful no-op otherwise).
    """
    model = MAIN_MODEL if tier == "main" else ROUTER_MODEL
    provider = _provider_of(model)
    bare = model.split("/", 1)[1]

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        llm = ChatOllama(model=bare, base_url=OLLAMA_BASE_URL, temperature=0.2)
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model=bare,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.2,
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        llm = ChatAnthropic(
            model=bare,
            anthropic_api_key=ANTHROPIC_API_KEY,
            temperature=0.2,
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model=bare, api_key=OPENAI_API_KEY, temperature=0.2)
    elif provider == "groq":
        from langchain_groq import ChatGroq

        llm = ChatGroq(model=bare, groq_api_key=GROQ_API_KEY, temperature=0.2)
    else:
        raise RuntimeError(f"Unhandled provider {provider!r}")

    # Late import to avoid a circular dep if observability ever imports config.
    from src.observability import get_langfuse_handler

    handler = get_langfuse_handler()
    if handler is not None:
        return llm.with_config({"callbacks": [handler]})
    return llm


# ---------- Embeddings ----------------------------------------------------

@lru_cache(maxsize=1)
def get_embeddings():
    """Return a langchain Embeddings instance. Cached so we instantiate once."""
    if USING_OLLAMA:
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)

    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(model=EMBED_MODEL, google_api_key=GOOGLE_API_KEY)
