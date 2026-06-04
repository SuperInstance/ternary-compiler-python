"""Tests for ternary-compiler."""

import pytest

from ternary_compiler import (
    Action,
    CompiledPolicy,
    Condition,
    StrategyIR,
    compile,
    optimize,
    profile,
)
from ternary_compiler.strategy_ir import Rule, TernaryValue


# ── TernaryValue tests ──────────────────────────────────────────────

def test_ternary_and():
    assert (TernaryValue.TRUE & TernaryValue.TRUE) == TernaryValue.TRUE
    assert (TernaryValue.TRUE & TernaryValue.FALSE) == TernaryValue.FALSE
    assert (TernaryValue.TRUE & TernaryValue.UNKNOWN) == TernaryValue.UNKNOWN
    assert (TernaryValue.FALSE & TernaryValue.UNKNOWN) == TernaryValue.FALSE


def test_ternary_or():
    assert (TernaryValue.FALSE | TernaryValue.FALSE) == TernaryValue.FALSE
    assert (TernaryValue.TRUE | TernaryValue.FALSE) == TernaryValue.TRUE
    assert (TernaryValue.UNKNOWN | TernaryValue.FALSE) == TernaryValue.UNKNOWN
    assert (TernaryValue.TRUE | TernaryValue.UNKNOWN) == TernaryValue.TRUE


def test_ternary_not():
    assert ~TernaryValue.TRUE == TernaryValue.FALSE
    assert ~TernaryValue.FALSE == TernaryValue.TRUE
    assert ~TernaryValue.UNKNOWN == TernaryValue.UNKNOWN


# ── Condition tests ─────────────────────────────────────────────────

def test_condition_eq():
    c = Condition(field="x", op="==", value=5)
    assert c.evaluate({"x": 5}) == TernaryValue.TRUE
    assert c.evaluate({"x": 3}) == TernaryValue.FALSE


def test_condition_unknown_field():
    c = Condition(field="z", op="==", value=1)
    assert c.evaluate({"x": 1}) == TernaryValue.UNKNOWN


def test_condition_comparison_ops():
    assert Condition("a", ">", 0).evaluate({"a": 5}) == TernaryValue.TRUE
    assert Condition("a", "<", 10).evaluate({"a": 5}) == TernaryValue.TRUE
    assert Condition("a", ">=", 5).evaluate({"a": 5}) == TernaryValue.TRUE
    assert Condition("a", "<=", 5).evaluate({"a": 5}) == TernaryValue.TRUE
    assert Condition("a", "!=", 3).evaluate({"a": 5}) == TernaryValue.TRUE


def test_condition_in():
    c = Condition("tag", "in", ["a", "b", "c"])
    assert c.evaluate({"tag": "b"}) == TernaryValue.TRUE
    assert c.evaluate({"tag": "z"}) == TernaryValue.FALSE


def test_condition_between():
    c = Condition("x", "between", 1, value_high=10)
    assert c.evaluate({"x": 5}) == TernaryValue.TRUE
    assert c.evaluate({"x": 0}) == TernaryValue.FALSE
    assert c.evaluate({"x": 10}) == TernaryValue.TRUE


# ── Rule tests ──────────────────────────────────────────────────────

def test_rule_and_logic():
    rule = Rule(
        conditions=(
            Condition("x", ">", 0),
            Condition("x", "<", 10),
        ),
        action=Action(type="accept"),
    )
    assert rule.evaluate({"x": 5}) == TernaryValue.TRUE
    assert rule.evaluate({"x": 15}) == TernaryValue.FALSE
    assert rule.evaluate({"x": -1}) == TernaryValue.FALSE


def test_rule_unknown_propagates():
    rule = Rule(
        conditions=(
            Condition("x", ">", 0),
            Condition("y", "==", 1),  # y not present
        ),
        action=Action(type="accept"),
    )
    assert rule.evaluate({"x": 5}) == TernaryValue.UNKNOWN


# ── Compiler tests ──────────────────────────────────────────────────

def test_compile_simple():
    ir = StrategyIR.from_simple(
        conditions=[[{"field": "x", "op": ">", "value": 0}]],
        actions=[{"type": "accept", "priority": 1}],
    )
    policy = compile(ir)
    assert policy.evaluate({"x": 5}) == "accept"
    assert policy.evaluate({"x": -1}) is None


def test_compile_priority_ordering():
    ir = StrategyIR.from_simple(
        conditions=[
            [{"field": "x", "op": ">", "value": 0}],
            [{"field": "x", "op": ">", "value": 100}],
        ],
        actions=[
            {"type": "low", "priority": 0},
            {"type": "high", "priority": 10},
        ],
    )
    policy = compile(ir)
    # x=150 matches both, but "high" has priority 10
    assert policy.evaluate({"x": 150}) == "high"


def test_compile_default_action():
    ir = StrategyIR.from_simple(
        conditions=[[{"field": "x", "op": ">", "value": 0}]],
        actions=[{"type": "accept", "priority": 1}],
        default={"type": "deny"},
    )
    policy = compile(ir)
    assert policy.evaluate({"x": -5}) == "deny"


# ── Optimizer tests ─────────────────────────────────────────────────

def test_optimizer_removes_tautology():
    rule = Rule(
        conditions=(Condition("x", "==", "x"), Condition("y", ">", 0)),
        action=Action(type="accept"),
    )
    optimized = optimize(StrategyIR(rules=[rule]))
    # Tautology "x == x" should be folded away
    assert len(optimized.rules) == 1
    assert len(optimized.rules[0].conditions) == 1
    assert optimized.rules[0].conditions[0].field == "y"


def test_optimizer_removes_contradiction():
    rule = Rule(
        conditions=(Condition("x", "!=", "x"),),
        action=Action(type="accept"),
    )
    optimized = optimize(StrategyIR(rules=[rule]))
    assert len(optimized.rules) == 0


def test_optimizer_removes_contradictory_range():
    rule = Rule(
        conditions=(Condition("x", ">", 10), Condition("x", "<", 5)),
        action=Action(type="accept"),
    )
    optimized = optimize(StrategyIR(rules=[rule]))
    assert len(optimized.rules) == 0


def test_optimizer_merges_duplicates():
    rule1 = Rule(
        conditions=(Condition("x", ">", 0),),
        action=Action(type="accept"),
    )
    rule2 = Rule(
        conditions=(Condition("x", ">", 0),),
        action=Action(type="accept"),
    )
    optimized = optimize(StrategyIR(rules=[rule1, rule2]))
    assert len(optimized.rules) == 1


# ── CompiledPolicy tests ───────────────────────────────────────────

def test_compiled_policy_evaluate_all():
    ir = StrategyIR.from_simple(
        conditions=[
            [{"field": "x", "op": ">", "value": 0}],
            [{"field": "x", "op": "<", "value": 10}],
        ],
        actions=[
            {"type": "positive", "priority": 1},
            {"type": "small", "priority": 2},
        ],
    )
    policy = compile(ir)
    results = policy.evaluate_all({"x": 5})
    assert "positive" in results
    assert "small" in results


def test_compiled_policy_detailed():
    ir = StrategyIR.from_simple(
        conditions=[[{"field": "x", "op": "==", "value": 42}]],
        actions=[{"type": "found", "priority": 5, "label": "answer"}],
    )
    policy = compile(ir)
    detail = policy.evaluate_detailed({"x": 42})
    assert detail["action"] == "found"
    assert detail["priority"] == 5
    assert detail["matched"] is True


def test_compiled_policy_cache():
    ir = StrategyIR.from_simple(
        conditions=[[{"field": "x", "op": ">", "value": 0}]],
        actions=[{"type": "ok", "priority": 1}],
    )
    policy = compile(ir)
    policy.enable_cache()
    assert policy.evaluate({"x": 5}) == "ok"
    assert policy.evaluate({"x": 5}) == "ok"
    assert len(policy._cache) == 1
    policy.disable_cache()
    assert len(policy._cache) == 0


def test_compiled_policy_stats():
    ir = StrategyIR.from_simple(
        conditions=[
            [{"field": "x", "op": ">", "value": 0}],
            [{"field": "y", "op": "<", "value": 10}],
        ],
        actions=[
            {"type": "a", "priority": 1},
            {"type": "b", "priority": 0},
        ],
        default={"type": "c"},
    )
    policy = compile(ir)
    stats = policy.stats()
    assert stats["rule_count"] == 2
    assert stats["has_default"] is True
    assert "x" in stats["fields"]
    assert "y" in stats["fields"]


# ── Profiler tests ──────────────────────────────────────────────────

def test_profiler_basic():
    ir = StrategyIR.from_simple(
        conditions=[[{"field": "x", "op": ">", "value": 0}]],
        actions=[{"type": "accept", "priority": 1}],
        default={"type": "deny"},
    )
    policy = compile(ir)
    envs = [{"x": 5}, {"x": -1}, {"x": 10}, {"x": 0}]
    result = profile(policy, envs)
    assert result.total_environments == 4
    assert result.matched == 2
    assert result.defaulted == 2
    assert result.action_counts.get("accept", 0) == 2
    assert result.action_counts.get("deny", 0) == 2


def test_profiler_summary():
    ir = StrategyIR.from_simple(
        conditions=[[{"field": "x", "op": ">", "value": 0}]],
        actions=[{"type": "ok", "priority": 1}],
    )
    policy = compile(ir)
    result = profile(policy, [{"x": 1}])
    summary = result.summary()
    assert "Environments: 1" in summary
    assert "Matched: 1" in summary
