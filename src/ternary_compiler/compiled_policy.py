"""Compiled policy — an optimized lookup table for fast evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ternary_compiler.strategy_ir import Action, Rule, TernaryValue


@dataclass
class CompiledPolicy:
    """A compiled policy with an ordered rule table and optional lookup cache.

    Evaluation checks rules in priority order (highest first).
    The first rule whose conditions all evaluate to TRUE fires.
    If no rule matches and a default action exists, it fires.
    Otherwise returns None.
    """

    rules: list[Rule] = field(default_factory=list)
    default_action: Action | None = None
    _cache: dict[tuple, str | None] = field(default_factory=dict, repr=False)
    _cache_enabled: bool = False

    def enable_cache(self, max_size: int = 1024) -> None:
        """Enable result caching for repeated environments."""
        self._cache_enabled = True
        self._cache_max = max_size
        self._cache.clear()

    def disable_cache(self) -> None:
        """Disable caching."""
        self._cache_enabled = False
        self._cache.clear()

    def _cache_key(self, env: dict[str, Any]) -> tuple:
        """Build a hashable cache key from env."""
        return tuple(sorted(env.items()))

    def evaluate(self, env: dict[str, Any]) -> str | None:
        """Evaluate the policy against an environment.

        Returns the action type string of the first matching rule,
        the default action type, or None.
        """
        if self._cache_enabled:
            key = self._cache_key(env)
            if key in self._cache:
                return self._cache[key]

        for rule in self.rules:
            result = rule.evaluate(env)
            if result == TernaryValue.TRUE:
                action_type = rule.action.type
                if self._cache_enabled:
                    self._cache[key] = action_type
                return action_type

        # No rule matched — try default
        action_type = self.default_action.type if self.default_action else None
        if self._cache_enabled:
            if len(self._cache) < self._cache_max:
                self._cache[key] = action_type
        return action_type

    def evaluate_all(self, env: dict[str, Any]) -> list[str]:
        """Return all matching action types (not just the first)."""
        results = []
        for rule in self.rules:
            if rule.evaluate(env) == TernaryValue.TRUE:
                results.append(rule.action.type)
        if not results and self.default_action:
            results.append(self.default_action.type)
        return results

    def evaluate_detailed(self, env: dict[str, Any]) -> dict[str, Any]:
        """Return detailed evaluation result with metadata."""
        for rule in self.rules:
            result = rule.evaluate(env)
            if result == TernaryValue.TRUE:
                return {
                    "action": rule.action.type,
                    "priority": rule.action.priority,
                    "label": rule.label,
                    "matched": True,
                    "ternary": result.value,
                }
        return {
            "action": self.default_action.type if self.default_action else None,
            "priority": self.default_action.priority if self.default_action else -1,
            "label": "default",
            "matched": False,
            "ternary": "default",
        }

    def stats(self) -> dict[str, Any]:
        """Return policy statistics."""
        return {
            "rule_count": len(self.rules),
            "has_default": self.default_action is not None,
            "cache_size": len(self._cache) if self._cache_enabled else 0,
            "fields": sorted({c.field for r in self.rules for c in r.conditions}),
        }
