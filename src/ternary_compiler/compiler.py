"""Compile StrategyIR into a CompiledPolicy with optimized rule ordering."""

from __future__ import annotations

from ternary_compiler.strategy_ir import StrategyIR, Rule
from ternary_compiler.compiled_policy import CompiledPolicy
from ternary_compiler.optimizer import optimize


def compile(
    strategy: StrategyIR,
    *,
    optimize_rules: bool = True,
) -> CompiledPolicy:
    """Compile a StrategyIR into a CompiledPolicy.

    Steps:
    1. Optionally run optimizer (dead code elimination, constant folding).
    2. Sort rules by priority (highest first) so the first match wins.
    3. Return a CompiledPolicy ready for fast evaluation.
    """
    rules = list(strategy.rules)

    if optimize_rules:
        optimized = optimize(StrategyIR(rules=rules, default_action=strategy.default_action))
        rules = list(optimized.rules)

    # Sort by priority descending (highest priority first)
    rules.sort(key=lambda r: r.action.priority, reverse=True)

    return CompiledPolicy(
        rules=rules,
        default_action=strategy.default_action,
    )
