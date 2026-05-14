"""Langfuse callback wiring.

`get_langfuse_handler()` returns a CallbackHandler when the LANGFUSE_*
env vars are set, else None. Every LLM and LangGraph call wired through
`make_langchain_llm` / `get_app` then auto-emits traces.

The handler import path moved across Langfuse SDK versions (>=2.50 → 3.x);
we try the new path first, fall back to the legacy one, and degrade to
a no-op if neither is available.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

log = logging.getLogger(__name__)


def _has_langfuse_keys() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


@lru_cache(maxsize=1)
def get_langfuse_handler():
    """Return a Langfuse CallbackHandler or None.

    Cached so we don't re-instantiate per LLM call (which would also re-create
    the underlying HTTP client and connection pool).
    """
    if not _has_langfuse_keys():
        return None

    # Langfuse SDK v3+ : `from langfuse.langchain import CallbackHandler`
    try:
        from langfuse.langchain import CallbackHandler

        handler = CallbackHandler()
        log.info("Langfuse tracing enabled (langfuse.langchain)")
        return handler
    except ImportError:
        pass

    # Legacy v2 path
    try:
        from langfuse.callback import CallbackHandler  # type: ignore

        handler = CallbackHandler(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
        log.info("Langfuse tracing enabled (langfuse.callback)")
        return handler
    except ImportError:
        log.warning("Langfuse keys set but no compatible SDK found; tracing disabled.")
        return None


def langfuse_callbacks() -> list:
    handler = get_langfuse_handler()
    return [handler] if handler is not None else []
