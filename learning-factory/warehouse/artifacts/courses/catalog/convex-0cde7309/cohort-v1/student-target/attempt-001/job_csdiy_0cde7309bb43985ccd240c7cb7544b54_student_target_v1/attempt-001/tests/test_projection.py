import unittest

from allocation_solver.projection import project_simplex


class ProjectionTests(unittest.TestCase):
    def assertVectorAlmostEqual(self, actual, expected, places=14):
        self.assertEqual(len(actual), len(expected))
        for left, right in zip(actual, expected):
            self.assertAlmostEqual(left, right, places=places)

    def test_zero_budget_returns_all_zeros(self):
        self.assertEqual(project_simplex((8.0, -3.0, 2.0), 0.0), (0.0, 0.0, 0.0))

    def test_already_feasible_vector_is_unchanged(self):
        vector = (0.2, 0.3, 0.5)
        self.assertVectorAlmostEqual(project_simplex(vector, 1.0), vector)

    def test_components_are_clipped_to_zero(self):
        self.assertVectorAlmostEqual(
            project_simplex((-1.0, 0.2, 2.0), 1.0),
            (0.0, 0.0, 1.0),
        )

    def test_sort_is_internal_and_original_order_is_preserved(self):
        projected = project_simplex((0.6, -0.2, 0.6), 1.0)
        self.assertVectorAlmostEqual(projected, (0.5, 0.0, 0.5))
        self.assertAlmostEqual(sum(projected), 1.0)
        self.assertTrue(all(value >= 0 for value in projected))


if __name__ == "__main__":
    unittest.main()

