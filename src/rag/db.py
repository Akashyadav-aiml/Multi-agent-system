"""pgvector connection helpers.

Centralizes DSN normalization and pgvector adapter registration so every
caller gets a connection that can read/write `vector` columns.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

import psycopg
from pgvector.psycopg import register_vector

from src.config import DATABASE_URL

log = logging.getLogger(__name__)


def _to_libpq_dsn(url: str) -> str:
    """SQLAlchemy uses 'postgresql+psycopg://...'; libpq wants 'postgresql://...'."""
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(_to_libpq_dsn(DATABASE_URL), autocommit=False)
    try:
        register_vector(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ping() -> bool:
    try:
        with connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return True
    except Exception as e:
        log.error("pgvector ping failed: %s", e)
        return False
