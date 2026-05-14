"""
Week 2: run the 3-agent crew (Planner → Researcher → Writer).

Usage:
    python scripts/run_week2.py "Compare LoRA vs full fine-tuning for LLMs"
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from src.agents.crew import run


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python scripts/run_week2.py "your research question"')
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    report = run(question)

    print("\n" + "=" * 70)
    print("FINAL REPORT")
    print("=" * 70)
    print(report)


if __name__ == "__main__":
    main()
