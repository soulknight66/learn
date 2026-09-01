import unittest

from allocation_solver.model import validate_input
from allocation_solver.solver import solve


def make_problem(items, budget=1.0, tolerance=1e-10, max_iterations=10000):
    return validate_input(
        {
            "budget": budget,
            "items": [
                {"id": item_id, "weight": weight, "target": target}
                for item_id, weight, target in items
            ],
            "solver": {
                "tolerance": tolerance,
                "max_iterations": max_iterations,
            },
        }
    )


class SolverExamples(unittest.TestCase):
    def test_one_item_is_fixed_by_constraint_at_iteration_zero(self):
        result = solve(make_problem([("only", 7.0, -100.0)], budget=2.0))
        self.assertEqual(result.status, "CONVERGED")
        self.assertEqual(result.allocation, (2.0,))
        self.assertEqual(result.diagnostics.iterations, 0)

    def test_symmetric_items_have_equal_allocation(self):
        result = solve(make_problem([("a", 3.0, 0.8), ("b", 3.0, 0.8)]))
        self.assertEqual(result.status, "CONVERGED")
        self.assertEqual(result.allocation, (0.5, 0.5))
        self.assertEqual(result.diagnostics.iterations, 0)

    def test_optimum_can_lie_on_nonnegativity_boundary(self):
        result = solve(
            make_problem(
                [("wanted", 1.0, 2.0), ("other", 1.0, -2.0)],
                max_iterations=1,
            )
        )
        self.assertEqual(result.status, "CONVERGED")
        self.assertAlmostEqual(result.allocation[0], 1.0)
        self.assertAlmostEqual(result.allocation[1], 0.0)
        self.assertEqual(result.diagnostics.iterations, 1)

    def test_zero_budget_is_the_all_zero_allocation(self):
        result = solve(make_problem([("a", 2.0, 4.0), ("b", 7.0, -3.0)], budget=0.0))
        self.assertEqual(result.status, "CONVERGED")
        self.assertEqual(result.allocation, (0.0, 0.0))
        self.assertEqual(result.diagnostics.iterations, 0)

    def test_negative_zero_budget_is_normalized(self):
        result = solve(make_problem([("only", 1.0, 2.0)], budget=-0.0))
        self.assertEqual(result.allocation, (0.0,))
        self.assertEqual(str(result.allocation[0]), "0.0")

    def test_iteration_exhaustion_is_not_convergence(self):
        result = solve(
            make_problem(
                [("slow", 1.0, 1.0), ("fast", 100.0, 0.0)],
                tolerance=1e-12,
                max_iterations=1,
            )
        )
        self.assertEqual(result.status, "MAX_ITERATIONS")
        self.assertEqual(result.diagnostics.iterations, 1)
        self.assertGreater(result.diagnostics.fixed_point_residual, 1e-12)
        self.assertLessEqual(result.diagnostics.feasibility_residual, 1e-12)

    def test_reported_residuals_describe_emitted_allocation(self):
        result = solve(make_problem([("a", 2.0, 0.9), ("b", 5.0, 0.1)]))
        self.assertEqual(result.status, "CONVERGED")
        self.assertLessEqual(
            result.diagnostics.fixed_point_residual,
            result.diagnostics.tolerance,
        )
        self.assertLessEqual(
            result.diagnostics.feasibility_residual,
            result.diagnostics.tolerance,
        )


class SolverPropertyTests(unittest.TestCase):
    def test_permutation_equivariance_after_matching_ids(self):
        items = [("api", 1.0, 1.2), ("batch", 3.0, 0.3), ("search", 9.0, -0.4)]
        first = solve(make_problem(items, budget=1.2, tolerance=1e-11))
        second = solve(make_problem([items[2], items[0], items[1]], budget=1.2, tolerance=1e-11))
        self.assertEqual(first.status, "CONVERGED")
        self.assertEqual(second.status, "CONVERGED")
        first_by_id = dict(zip((row[0] for row in items), first.allocation))
        permuted = [items[2], items[0], items[1]]
        second_by_id = dict(zip((row[0] for row in permuted), second.allocation))
        for item_id in first_by_id:
            self.assertAlmostEqual(first_by_id[item_id], second_by_id[item_id], places=10)

    def test_scaling_all_weights_preserves_optimizer(self):
        items = [("a", 1.0, 1.2), ("b", 3.0, 0.3), ("c", 9.0, -0.4)]
        scaled = [(item_id, weight * 11.0, target) for item_id, weight, target in items]
        first = solve(make_problem(items, budget=1.2, tolerance=1e-11))
        second = solve(make_problem(scaled, budget=1.2, tolerance=1e-11))
        self.assertEqual(first.status, "CONVERGED")
        self.assertEqual(second.status, "CONVERGED")
        for left, right in zip(first.allocation, second.allocation):
            self.assertAlmostEqual(left, right, places=10)

    def test_against_independent_two_item_grid_oracle(self):
        problem = make_problem([("a", 2.0, 0.8), ("b", 5.0, 0.1)], tolerance=1e-12)
        result = solve(problem)
        self.assertEqual(result.status, "CONVERGED")

        # This oracle enumerates only points spaced h=0.001 apart. Its best
        # allocation can localize the continuous minimizer only to one grid cell.
        h = 0.001
        candidates = []
        for index in range(1001):
            first = index * h
            second = 1.0 - first
            value = 0.5 * (2.0 * (first - 0.8) ** 2 + 5.0 * (second - 0.1) ** 2)
            candidates.append((value, first, second))
        grid_value, grid_first, grid_second = min(candidates)

        self.assertLessEqual(result.objective, grid_value + 1e-14)
        self.assertLessEqual(abs(result.allocation[0] - grid_first), h)
        self.assertLessEqual(abs(result.allocation[1] - grid_second), h)


if __name__ == "__main__":
    unittest.main()
