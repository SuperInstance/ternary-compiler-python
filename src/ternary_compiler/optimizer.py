"""Optimizer — dead code elimination and constant folding for strategies."""

from __future__ import annotations

from ternary_compiler.strategy_ir import (
    Action,
    Condition,
    Rule,
    StrategyIR,
    TernaryValue,
)


def _is_tautology(condition: Condition) -> bool:
    """Check if a condition is always true (e.g., field == field)."""
    return condition.op == "==" and condition.field == condition.value


def _is_contradiction(condition: Condition) -> bool:
    """Check if a condition is always false (e.g., field != field)."""
    return condition.op == "!=" and condition.field == condition.value


def _fold_constants(conditions: tuple[Condition, ...]) -> tuple[Condition, ...]:
    """Remove tautologies (always true) from conditions."""
    return tuple(c for c in conditions if not _is_tautology(c))


def _is_unsatisfiable(conditions: tuple[Condition, ...]) -> bool:
    """Check if conditions contain a contradiction."""
    return any(_is_contradiction(c) for c in conditions)


def _find_contradictory_pairs(conditions: tuple[Condition, ...]) -> bool:
    """Find mutually exclusive conditions on the same field."""
    # Quick check: same field with contradictory ops
    by_field: dict[str, list[Condition]] = {}
    for c in conditions:
        by_field.setdefault(c.field, []).append(c)

    for field, conds in by_field.items():
        # Check for x > 5 and x < 3 type contradictions
        uppers = [c.value for c in conds if c.op in ("<", "<=")]
        lowers = [c.value for c in conds if c.op in (">", ">=")]
        if uppers and lowers:
            min_upper = min(uppers)
            max_lower = max(lowers)
            if min_upper <= max_lower:
                # Could be tighter, but at least check strict
                has_strict = any(c.op == "<" or c.op == ">" for c in conds)
                if has_strict and min_upper == max_lower:
                    return True
                if min_upper < max_lower:
                    return True
    return False


def _eliminate_shadowed_rules(rules: list[Rule]) -> list[Rule]:
    """Remove rules that can never fire because a higher-priority rule always matches.

    Simple heuristic: if a rule has no conditions and same priority scope, lower rules are shadowed.
    """
    result = []
    for i, rule in enumerate(rules):
        # Keep the rule unless a previous unconditional rule with >= priority covers it
        shadowed = False
        for prev in result:
            if (
                len(prev.conditions) == 0
                and prev.action.priority >= rule.action.priority
            ):
                shadowed = True
                break
        if not shadowed:
            result.append(rule)
    return result


def _merge_duplicate_rules(rules: list[Rule]) -> list[Rule]:
    """Merge rules with identical conditions and action type but different params."""
    seen: dict[tuple, Rule] = {}
    for rule in rules:
        key = (rule.conditions, rule.action.type)
        if key not in seen:
            seen[key] = rule
    return list(seen.values())


def optimize(strategy: StrategyIR) -> StrategyIR:
    """Run all optimization passes on a StrategyIR.

    Passes:
    1. Constant folding — remove tautological conditions.
    2. Dead code elimination — remove unsatisfiable rules.
    3. Contradictory pair detection — remove rules with contradictory conditions.
    4. Duplicate merging — deduplicate identical rules.
    5. Shadowed rule elimination — remove rules shadowed by unconditional higher-priority rules.
    """
    optimized_rules: list[Rule] = []

    for rule in strategy.rules:
        # Pass 1: constant folding
        conditions = _fold_constants(rule.conditions)

        # Pass 2: unsatisfiable check
        if _is_unsatisfiable(conditions):
            continue

        # Pass 3: contradictory pairs
        if _find_contradictory_pairs(conditions):
            continue

        # Reconstruct rule with folded conditions
        optimized_rules.append(Rule(
            conditions=conditions if conditions else rule.conditions,
            action=rule.action,
            label=rule.label,
        ))

    # Pass 4: merge duplicates
    optimized_rules = _merge_duplicate_rules(optimized_rules)

    # Pass 5: shadowed rule elimination
    optimized_rules = _eliminate_shadowed_rules(optimized_rules)

    return StrategyIR(
        rules=optimized_rules,
        default_action=strategy.default_action,
    )
