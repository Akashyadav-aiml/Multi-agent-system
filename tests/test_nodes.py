"""Unit tests for src.graph.nodes — LLM stubbed, no network."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.graph import nodes


class _FakeLLM:
    def __init__(self, content: str):
        self._content = content

    def invoke(self, prompt):  # noqa: ARG002 — signature must match real LLM
        return SimpleNamespace(content=self._content)


# ---------- plan_node ------------------------------------------------------

def test_plan_node_parses_valid_json():
    fake = _FakeLLM('{"sub_questions": ["q1", "q2", "q3"]}')
    with patch.object(nodes, "make_langchain_llm", return_value=fake):
        out = nodes.plan_node({"question": "original"})
    assert out["sub_questions"] == ["q1", "q2", "q3"]
    assert out["iterations"] == 0


def test_plan_node_falls_back_on_unparseable():
    fake = _FakeLLM("not json at all")
    with patch.object(nodes, "make_langchain_llm", return_value=fake):
        out = nodes.plan_node({"question": "original"})
    assert out["sub_questions"] == ["original"]  # fallback uses raw question
    assert out["iterations"] == 0


def test_plan_node_strips_json_from_fences():
    fake = _FakeLLM('```json\n{"sub_questions": ["a", "b"]}\n```')
    with patch.object(nodes, "make_langchain_llm", return_value=fake):
        out = nodes.plan_node({"question": "x"})
    assert out["sub_questions"] == ["a", "b"]


# ---------- fact_check_node ------------------------------------------------

def test_fact_check_grounded_true_increments_iterations():
    fake = _FakeLLM('{"grounded": true, "rationale": ""}')
    state = {"draft": "d", "chunks": [], "iterations": 1}
    with patch.object(nodes, "make_langchain_llm", return_value=fake):
        out = nodes.fact_check_node(state)
    assert out["fact_check"]["grounded"] is True
    assert out["iterations"] == 2


def test_fact_check_fails_open_when_unparseable():
    fake = _FakeLLM("garbage")
    state = {"draft": "d", "chunks": [], "iterations": 0}
    with patch.object(nodes, "make_langchain_llm", return_value=fake):
        out = nodes.fact_check_node(state)
    # Fail-open: don't loop forever just because the judge couldn't be parsed.
    assert out["fact_check"]["grounded"] is True
    assert out["iterations"] == 1


# ---------- should_retry ---------------------------------------------------

def test_should_retry_grounded_goes_to_write():
    state = {"fact_check": {"grounded": True}, "iterations": 1}
    assert nodes.should_retry(state) == "write"


def test_should_retry_not_grounded_loops_to_research():
    state = {"fact_check": {"grounded": False}, "iterations": 1}
    assert nodes.should_retry(state) == "research"


def test_should_retry_exhausted_iterations_ships_draft():
    state = {"fact_check": {"grounded": False}, "iterations": nodes.MAX_ITERATIONS}
    assert nodes.should_retry(state) == "write"


def test_should_retry_missing_fact_check_treats_as_ungrounded():
    state = {"iterations": 0}
    # No fact_check yet → defaults to grounded=False → research
    assert nodes.should_retry(state) == "research"


# ---------- _parse_json_strict --------------------------------------------

def test_parse_json_strict_handles_trailing_prose():
    from src.graph.nodes import PlanOutput, _parse_json_strict

    parsed = _parse_json_strict(
        PlanOutput,
        'Here you go:\n{"sub_questions": ["x", "y"]}\n— hope that helps',
    )
    assert parsed is not None
    assert parsed.sub_questions == ["x", "y"]


def test_parse_json_strict_returns_none_on_garbage():
    from src.graph.nodes import PlanOutput, _parse_json_strict

    assert _parse_json_strict(PlanOutput, "no json here") is None
