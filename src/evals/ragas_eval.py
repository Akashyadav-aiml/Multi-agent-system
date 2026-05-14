"""Ragas evaluation harness.

Runs the LangGraph workflow over the golden set and scores each answer with
faithfulness, answer relevancy, context precision, and context recall.

Usage:
    python -m src.evals.ragas_eval                   # all questions, default judge
    python -m src.evals.ragas_eval --limit 5         # smoke test on first 5
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import typer

from src.config import MAIN_MODEL, make_langchain_llm
from src.graph.workflow import get_app
from src.logging_setup import configure_logging

GOLDEN = Path(__file__).resolve().parent / "golden_set.json"
RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "eval_results"

log = logging.getLogger(__name__)

app = typer.Typer(add_completion=False, help="Run Ragas evaluation on the golden set.")


def _load_golden() -> list[dict[str, Any]]:
    with GOLDEN.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list) or not data:
        raise RuntimeError(f"{GOLDEN} is empty or malformed")
    return data


def _run_workflow_on(items: list[dict]) -> list[dict]:
    graph = get_app()
    records: list[dict] = []
    for i, item in enumerate(items, 1):
        q = item["question"]
        log.info("[%d/%d] %s", i, len(items), q)
        try:
            result = graph.invoke(
                {"question": q, "iterations": 0},
                config={"configurable": {"thread_id": f"eval-{i}"}},
            )
        except Exception as e:
            log.exception("workflow failed for %r", q)
            records.append({
                "question": q,
                "answer": f"<workflow error: {e!s}>",
                "contexts": [],
                "ground_truth": item.get("ground_truth", ""),
            })
            continue

        answer = result.get("final_report") or result.get("draft") or ""
        contexts = [c.get("content", "") for c in (result.get("chunks") or []) if c.get("content")]
        records.append({
            "question": q,
            "answer": answer,
            "contexts": contexts or ["(no retrieved context)"],
            "ground_truth": item.get("ground_truth", ""),
        })
    return records


def _evaluate(records: list[dict]) -> dict[str, Any]:
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )

    judge = make_langchain_llm("router")  # cheap classifier for LLM-as-judge
    ds = Dataset.from_list(records)
    result = evaluate(
        ds,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=judge,
    )
    # result is a Ragas EvaluationResult; .to_pandas() / dict-like access supported.
    try:
        scores = {k: float(v) for k, v in result.scores.items()} if hasattr(result, "scores") else dict(result)
    except Exception:
        scores = {"raw": str(result)}
    return scores


@app.command()
def main(
    limit: int = typer.Option(0, "--limit", "-n", min=0, help="0 = full golden set."),
    log_level: str = typer.Option("INFO", "--log-level"),
) -> None:
    configure_logging(log_level)
    golden = _load_golden()
    items = golden if limit == 0 else golden[:limit]
    log.info("Running workflow on %d question(s) using model=%s", len(items), MAIN_MODEL)

    records = _run_workflow_on(items)

    log.info("Scoring with Ragas...")
    scores = _evaluate(records)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = RESULTS_DIR / f"results_{stamp}.json"
    out.write_text(json.dumps({"model": MAIN_MODEL, "scores": scores, "records": records}, indent=2))

    typer.echo("\n=== Ragas scores ===")
    for k, v in scores.items():
        typer.echo(f"  {k:24s} {v}")
    typer.echo(f"\nFull results written to {out}")


if __name__ == "__main__":
    app()
