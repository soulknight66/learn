"""Projected-gradient solver core with explicit convergence diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

from .model import NumericalFailure, Problem, gradient, objective
from .projection import project_simplex


@dataclass(frozen=True)
class Diagnostics:
    iterations: int
    tolerance: float
    fixed_point_residual: float
    feasibility_residual: float


@dataclass(frozen=True)
class SolveResult:
    status: str
    allocation: tuple[float, ...]
    objective: float
    diagnostics: Diagnostics


def projected_update(problem: Problem, allocation: Sequence[float]) -> tuple[float, ...]:
    lipschitz = max(item.weight for item in problem.items)
    components = gradient(problem, allocation)
    try:
        stepped = tuple(
            amount - component / lipschitz
            for amount, component in zip(allocation, components)
        )
    except OverflowError:
        raise NumericalFailure("numerical result is not finite") from None
    if not all(math.isfinite(value) for value in stepped):
        raise NumericalFailure("numerical result is not finite")
    return project_simplex(stepped, problem.budget)


def fixed_point_residual(problem: Problem, allocation: Sequence[float]) -> float:
    updated = projected_update(problem, allocation)
    residual = max(abs(after - before) for after, before in zip(updated, allocation))
    if not math.isfinite(residual):
        raise NumericalFailure("numerical result is not finite")
    return residual


def feasibility_residual(problem: Problem, allocation: Sequence[float]) -> float:
    try:
        total = math.fsum(allocation)
    except OverflowError:
        raise NumericalFailure("numerical result is not finite") from None
    nonnegativity = max(max(-value, 0.0) for value in allocation)
    residual = max(abs(total - problem.budget), nonnegativity)
    if not math.isfinite(total) or not math.isfinite(residual):
        raise NumericalFailure("numerical result is not finite")
    return residual


def _diagnostics(problem: Problem, allocation: Sequence[float], iterations: int) -> Diagnostics:
    return Diagnostics(
        iterations=iterations,
        tolerance=problem.solver.tolerance,
        fixed_point_residual=fixed_point_residual(problem, allocation),
        feasibility_residual=feasibility_residual(problem, allocation),
    )


def _is_converged(diagnostics: Diagnostics) -> bool:
    return (
        diagnostics.fixed_point_residual <= diagnostics.tolerance
        and diagnostics.feasibility_residual <= diagnostics.tolerance
    )


def solve(problem: Problem) -> SolveResult:
    """Run bounded PGD and report residuals for the emitted allocation."""

    count = len(problem.items)
    initial_amount = problem.budget / count
    if not math.isfinite(initial_amount):
        raise NumericalFailure("numerical result is not finite")
    allocation = tuple(initial_amount for _ in problem.items)

    diagnostics = _diagnostics(problem, allocation, 0)
    if _is_converged(diagnostics):
        return SolveResult(
            status="CONVERGED",
            allocation=allocation,
            objective=objective(problem, allocation),
            diagnostics=diagnostics,
        )

    for iteration in range(1, problem.solver.max_iterations + 1):
        allocation = projected_update(problem, allocation)
        diagnostics = _diagnostics(problem, allocation, iteration)
        if _is_converged(diagnostics):
            return SolveResult(
                status="CONVERGED",
                allocation=allocation,
                objective=objective(problem, allocation),
                diagnostics=diagnostics,
            )

    return SolveResult(
        status="MAX_ITERATIONS",
        allocation=allocation,
        objective=objective(problem, allocation),
        diagnostics=diagnostics,
    )

