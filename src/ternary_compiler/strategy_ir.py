"""Strategy intermediate representation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TernaryValue(Enum):
    """Three-valued logic: TRUE, FALSE, or UNKNOWN."""

    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"

    def __and__(self, other: TernaryValue) -> TernaryValue:
        """Kleene AND."""
        if self == TernaryValue.FALSE or other == TernaryValue.FALSE:
            return TernaryValue.FALSE
        if self == TernaryValue.UNKNOWN or other == TernaryValue.UNKNOWN:
            return TernaryValue.UNKNOWN
        return TernaryValue.TRUE

    def __or__(self, other: TernaryValue) -> TernaryValue:
        """Kleene OR."""
        if self == TernaryValue.TRUE or other == TernaryValue.TRUE:
            return TernaryValue.TRUE
        if self == TernaryValue.UNKNOWN or other == TernaryValue.UNKNOWN:
            return TernaryValue.UNKNOWN
        return TernaryValue.FALSE

    def __invert__(self) -> TernaryValue:
        """Negation."""
        if self == TernaryValue.TRUE:
            return TernaryValue.FALSE
        if self == TernaryValue.FALSE:
            return TernaryValue.TRUE
        return TernaryValue.UNKNOWN


@dataclass(frozen=True)
class Condition:
    """A single comparison condition: field op value."""

    field: str
    op: str  # "==", "!=", ">", "<", ">=", "<=", "in", "not_in", "between"
    value: Any = None
    value_high: Any = None  # for "between"

    def evaluate(self, env: dict[str, Any]) -> TernaryValue:
        """Evaluate condition against an environment dict."""
        if self.field not in env:
            return TernaryValue.UNKNOWN
        actual = env[self.field]
        try:
            match self.op:
                case "==":
                    return TernaryValue.TRUE if actual == self.value else TernaryValue.FALSE
                case "!=":
                    return TernaryValue.TRUE if actual != self.value else TernaryValue.FALSE
                case ">":
                    return TernaryValue.TRUE if actual > self.value else TernaryValue.FALSE
                case "<":
                    return TernaryValue.TRUE if actual < self.value else TernaryValue.FALSE
                case ">=":
                    return TernaryValue.TRUE if actual >= self.value else TernaryValue.FALSE
                case "<=":
                    return TernaryValue.TRUE if actual <= self.value else TernaryValue.FALSE
                case "in":
                    return TernaryValue.TRUE if actual in self.value else TernaryValue.FALSE
                case "not_in":
                    return TernaryValue.TRUE if actual not in self.value else TernaryValue.FALSE
                case "between":
                    lo, hi = self.value, self.value_high
                    return TernaryValue.TRUE if lo <= actual <= hi else TernaryValue.FALSE
                case _:
                    return TernaryValue.UNKNOWN
        except (TypeError, ValueError):
            return TernaryValue.UNKNOWN


@dataclass(frozen=True)
class Action:
    """An action to take when a rule fires."""

    type: str
    priority: int = 0
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Rule:
    """A single rule: if all conditions hold (AND), fire the action."""

    conditions: tuple[Condition, ...]
    action: Action
    label: str = ""

    def evaluate(self, env: dict[str, Any]) -> TernaryValue:
        """Evaluate all conditions with Kleene AND."""
        result = TernaryValue.TRUE
        for cond in self.conditions:
            result = result & cond.evaluate(env)
        return result


@dataclass
class StrategyIR:
    """Intermediate representation of a ternary strategy.

    Contains an ordered list of rules. During evaluation, rules are
    checked in priority order (highest first). The first matching rule
    fires its action.
    """

    rules: list[Rule] = field(default_factory=list)
    default_action: Action | None = None

    # Convenience constructors
    @staticmethod
    def from_simple(
        conditions: list[dict],
        actions: list[dict],
        default: dict | None = None,
    ) -> StrategyIR:
        """Build a StrategyIR from simple dicts (for ergonomic API)."""
        rules = []
        for cond_list, act_dict in zip(conditions, actions):
            conds = []
            if isinstance(cond_list, dict):
                cond_list = [cond_list]
            for c in cond_list:
                conds.append(Condition(
                    field=c["field"],
                    op=c["op"],
                    value=c.get("value"),
                    value_high=c.get("value_high"),
                ))
            action = Action(
                type=act_dict["type"],
                priority=act_dict.get("priority", 0),
                params=act_dict.get("params", {}),
            )
            rules.append(Rule(conditions=tuple(conds), action=action, label=act_dict.get("label", "")))
        default_action = None
        if default:
            default_action = Action(
                type=default["type"],
                priority=default.get("priority", 0),
                params=default.get("params", {}),
            )
        return StrategyIR(rules=rules, default_action=default_action)
