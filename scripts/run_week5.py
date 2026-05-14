"""Week 5: run the LangGraph workflow.

Usage:
    python scripts/run_week5.py "What are recent advances in mixture of experts models?"
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from src.graph.workflow import get_app
from src.logging_setup import configure_logging


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python scripts/run_week5.py "your research question"')
        sys.exit(1)

    configure_logging()
    question = " ".join(sys.argv[1:])

    app = get_app()
    print(f"\n[?] {question}\n")
    print("-- streaming nodes --")
    final: dict = {}
    for event in app.stream(
        {"question": question, "iterations": 0},
        config={"configurable": {"thread_id": "cli"}},
        stream_mode="updates",
    ):
        for node, update in event.items():
            keys = ", ".join(sorted(update.keys())) if isinstance(update, dict) else "?"
            print(f"  • {node:12s}  updated: {keys}")
            final.update(update if isinstance(update, dict) else {})

    print("\n" + "=" * 70)
    print("FINAL REPORT")
    print("=" * 70)
    print(final.get("final_report") or final.get("draft") or "(no output)")


if __name__ == "__main__":
    main()
