"""Input contracts and mathematical primitives for the allocation model."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from typing import Any, Sequence


COURSE_ID = "course_0cde7309bb43985ccd240c7cb7544b54"
UNIT_ID = "unit_kickoff_trustworthy_convex_allocation_v1"
ALGORITHM = "projected_gradient_simplex_v1"
VALIDATION_LABEL = "LEARNER_GENERATED_NOT_INDEPENDENTLY_VALIDATED"


class InvalidInput(ValueError):
    """A stable, user-facing input contract violation."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class NumericalFailure(ArithmeticError):
    """A valid model whose floating-point evaluation became non-finite."""


@dataclass(frozen=True)
class Item:
    item_id: str
    weight: float
    target: float


@dataclass(frozen=True)
class SolverOptions:
    tolerance: float
    max_iterations: int


@dataclass(frozen=True)
class Problem:
    budget: float
    items: tuple[Item, ...]
    solver: SolverOptions


def _invalid(code: str, message: str) -> InvalidInput:
    return InvalidInput(code, message)


def _is_finite_json_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    # Python integers are finite even when they are too large for binary64.
    # Their eventual conversion is part of numerical evaluation, not syntax
    # validation, and can therefore produce NUMERICAL_FAILURE honestly.
    return isinstance(value, int) or math.isfinite(value)


def parse_input_bytes(raw: bytes) -> Problem:
    """Decode, validate, and normalize one UTF-8 JSON input document."""

    try:
        decoded = raw.decode("utf-8")
        value = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError):
        raise _invalid("INVALID_JSON", "input is not valid UTF-8 JSON") from None
    return validate_input(value)


def validate_input(value: Any) -> Problem:
    """Validate with documented category precedence and convert to binary64."""

    if not isinstance(value, dict):
        raise _invalid("INVALID_STRUCTURE", "root must be an object")

    for field in ("budget", "items", "solver"):
        if field not in value:
            raise _invalid("INVALID_STRUCTURE", f"root is missing required field {field}")

    items_value = value["items"]
    solver_value = value["solver"]
    if not isinstance(solver_value, dict):
        raise _invalid("INVALID_STRUCTURE", "solver must be an object")
    if not isinstance(items_value, list) or not items_value:
        raise _invalid("INVALID_STRUCTURE", "items must be a nonempty array")

    for field in ("tolerance", "max_iterations"):
        if field not in solver_value:
            raise _invalid("INVALID_STRUCTURE", f"solver is missing required field {field}")

    for index, item_value in enumerate(items_value):
        if not isinstance(item_value, dict):
            raise _invalid("INVALID_STRUCTURE", f"item {index} must be an object")
        for field in ("id", "weight", "target"):
            if field not in item_value:
                raise _invalid(
                    "INVALID_STRUCTURE", f"item {index} is missing required field {field}"
                )

    numeric_values: list[tuple[str, Any]] = [("budget", value["budget"])]
    for index, item_value in enumerate(items_value):
        numeric_values.extend(
            (
                (f"item {index} weight", item_value["weight"]),
                (f"item {index} target", item_value["target"]),
            )
        )
    numeric_values.append(("tolerance", solver_value["tolerance"]))

    for label, numeric_value in numeric_values:
        if not _is_finite_json_number(numeric_value):
            raise _invalid("INVALID_NUMERIC", f"{label} must be a finite number")

    max_iterations = solver_value["max_iterations"]
    if isinstance(max_iterations, bool) or not isinstance(max_iterations, int):
        raise _invalid("INVALID_NUMERIC", "max_iterations must be an integer")

    budget_value = value["budget"]
    tolerance_value = solver_value["tolerance"]
    if budget_value < 0:
        raise _invalid("INVALID_RANGE", "budget must be nonnegative")
    for index, item_value in enumerate(items_value):
        if item_value["weight"] <= 0:
            raise _invalid("INVALID_RANGE", f"item {index} weight must be positive")
    if not (0 < tolerance_value <= 1e-3):
        raise _invalid("INVALID_RANGE", "tolerance must be in (0, 1e-3]")
    if not (1 <= max_iterations <= 1_000_000):
        raise _invalid("INVALID_RANGE", "max_iterations must be in [1, 1000000]")

    seen_ids: set[str] = set()
    for index, item_value in enumerate(items_value):
        item_id = item_value["id"]
        if not isinstance(item_id, str) or not item_id:
            raise _invalid("INVALID_ITEM_ID", f"item {index} id must be a nonempty string")
        if item_id in seen_ids:
            raise _invalid("INVALID_ITEM_ID", "item ids must be unique")
        seen_ids.add(item_id)

    try:
        budget = float(budget_value)
        if budget == 0.0:
            budget = 0.0
        tolerance = float(tolerance_value)
        items = tuple(
            Item(
                item_id=item_value["id"],
                weight=float(item_value["weight"]),
                target=float(item_value["target"]),
            )
            for item_value in items_value
        )
    except (OverflowError, ValueError):
        raise NumericalFailure("numerical result is not finite") from None

    normalized = [budget, tolerance]
    normalized.extend(item.weight for item in items)
    normalized.extend(item.target for item in items)
    if not all(math.isfinite(number) for number in normalized):
        raise NumericalFailure("numerical result is not finite")

    return Problem(
        budget=budget,
        items=items,
        solver=SolverOptions(tolerance=tolerance, max_iterations=max_iterations),
    )


def gradient(problem: Problem, allocation: Sequence[float]) -> tuple[float, ...]:
    if len(allocation) != len(problem.items):
        raise ValueError("allocation length does not match items")
    values: list[float] = []
    for item, amount in zip(problem.items, allocation):
        try:
            component = item.weight * (amount - item.target)
        except OverflowError:
            raise NumericalFailure("numerical result is not finite") from None
        if not math.isfinite(component):
            raise NumericalFailure("numerical result is not finite")
        values.append(component)
    return tuple(values)


def objective(problem: Problem, allocation: Sequence[float]) -> float:
    if len(allocation) != len(problem.items):
        raise ValueError("allocation length does not match items")
    terms: list[float] = []
    for item, amount in zip(problem.items, allocation):
        try:
            difference = amount - item.target
            term = 0.5 * item.weight * difference * difference
        except OverflowError:
            raise NumericalFailure("numerical result is not finite") from None
        if not math.isfinite(term):
            raise NumericalFailure("numerical result is not finite")
        terms.append(term)
    try:
        result = math.fsum(terms)
    except OverflowError:
        raise NumericalFailure("numerical result is not finite") from None
    if not math.isfinite(result):
        raise NumericalFailure("numerical result is not finite")
    return result
