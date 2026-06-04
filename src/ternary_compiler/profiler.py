"""Profiler — evaluate a compiled policy against environments and collect stats."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ternary_compiler.compiled_policy import CompiledPolicy
from ternary_compiler.strategy_ir import TernaryValue


@dataclass
class ProfileResult:
    """Results from profiling a policy against a set of environments."""

    total_environments: int = 0
    matched: int = 0
    defaulted: int = 0
    unknown: int = 0
    action_counts: dict[str, int] = field(default_factory=dict)
    avg_conditions_checked: float = 0.0
    max_conditions_checked: int = 0
    min_conditions_checked: int = 0

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            f"Environments: {self.total_environments}",
            f"Matched: {self.matched} ({self.matched / max(self.total_environments, 1) * 100:.1f}%)",
            f"Defaulted: {self.defaulted}",
            f"Unknown/no match: {self.unknown}",
            f"Avg conditions checked: {self.avg_conditions_checked:.1f}",
            f"Action distribution: {self.action_counts}",
        ]
        return "\n".join(lines)


def profile(
    policy: CompiledPolicy,
    environments: list[dict[str, Any]],
) -> ProfileResult:
    """Profile a compiled policy against a list of environments.

    Returns a ProfileResult with statistics on match rates, action
    distribution, and evaluation cost.
    """
    result = ProfileResult(
        total_environments=len(environments),
        min_conditions_checked=float("inf"),
        max_conditions_checked=0,
    )
    total_conditions = 0

    for env in environments:
        matched = False
        conditions_checked = 0

        for rule in policy.rules:
            for cond in rule.conditions:
                conditions_checked += 1
                val = cond.evaluate(env)
                if val == TernaryValue.FALSE:
                    break  # short-circuit AND

            rule_result = rule.evaluate(env)
            if rule_result == TernaryValue.TRUE:
                matched = True
                action_type = rule.action.type
                result.action_counts[action_type] = result.action_counts.get(action_type, 0) + 1
                result.matched += 1
                break

        total_conditions += conditions_checked

        if not matched:
            if policy.default_action:
                result.defaulted += 1
                action_type = policy.default_action.type
                result.action_counts[action_type] = result.action_counts.get(action_type, 0) + 1
            else:
                result.unknown += 1

        result.max_conditions_checked = max(result.max_conditions_checked, conditions_checked)
        result.min_conditions_checked = min(result.min_conditions_checked, conditions_checked)

    if result.total_environments > 0:
        result.avg_conditions_checked = total_conditions / result.total_environments

    if result.min_conditions_checked == float("inf"):
        result.min_conditions_checked = 0

    return result
