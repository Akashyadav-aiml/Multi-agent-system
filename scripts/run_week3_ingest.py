"""Week 3: bulk-ingest arXiv papers on a topic into pgvector.

Usage:
    python scripts/run_week3_ingest.py --topic "retrieval augmented generation" --limit 50
    python scripts/run_week3_ingest.py --topic "mixture of experts" --limit 30 --chunk-size 600
"""
from __future__ import annotations

import sys

import typer

sys.path.insert(0, ".")

from src.logging_setup import configure_logging
from src.rag.db import ping
from src.rag.ingest import ingest_topic

app = typer.Typer(add_completion=False, help="Ingest arXiv papers into pgvector.")


@app.command()
def main(
    topic: str = typer.Option(..., "--topic", "-t", help="arXiv search topic."),
    limit: int = typer.Option(50, "--limit", "-n", min=1, max=500, help="Max papers to ingest."),
    chunk_size: int = typer.Option(800, "--chunk-size", min=200, max=4000),
    chunk_overlap: int = typer.Option(120, "--chunk-overlap", min=0, max=1000),
    log_level: str = typer.Option("INFO", "--log-level"),
) -> None:
    configure_logging(log_level)

    if not ping():
        typer.echo("pgvector is unreachable. Did you run `docker compose up -d`?", err=True)
        raise typer.Exit(code=1)

    stats = ingest_topic(
        topic,
        limit=limit,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    typer.echo("\n=== Ingest summary ===")
    typer.echo(f"  arXiv results:   {stats.papers_seen}")
    typer.echo(f"  papers inserted: {stats.papers_inserted}")
    typer.echo(f"  papers skipped:  {stats.skipped}")
    typer.echo(f"  chunks inserted: {stats.chunks_inserted}")


if __name__ == "__main__":
    app()
