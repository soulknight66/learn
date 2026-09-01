import importlib.util
import os
import unittest


PATH = os.path.join(os.path.dirname(__file__), "candidate.py")
SPEC = importlib.util.spec_from_file_location("budget_candidate", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BudgetTests(unittest.TestCase):
    def test_exact_limit_is_allowed(self):
        budget = MODULE.Budget(3)
        for unused in range(3):
            budget.consume()
        with self.assertRaises(MODULE.BudgetExceeded):
            budget.consume()


if __name__ == "__main__":
    unittest.main()
