import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "review_exercises" / "tail_position" / "candidate.py"


def load_candidate():
    specification = importlib.util.spec_from_file_location(
        "tail_position_candidate", CANDIDATE
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("could not load tail-position review candidate")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class TailPositionExerciseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate = load_candidate()

    def evaluate_special(self, name, arguments):
        seen = []

        def evaluate(form, _environment):
            seen.append(form)
            return form

        result = self.candidate.evaluate_special(name, arguments, {}, evaluate)
        return result, seen

    def test_if_uses_pebble_truthiness_and_optional_else(self):
        self.assertEqual(self.evaluate_special("if", [0, "then", "else"]), ("then", [0, "then"]))
        self.assertEqual(self.evaluate_special("if", [False, "then"]), (None, [False]))

    def test_do_handles_empty_and_orders_nonfinal_forms(self):
        self.assertEqual(self.evaluate_special("do", []), (None, []))
        self.assertEqual(self.evaluate_special("do", [1, 2, 3]), (3, [1, 2, 3]))

    def test_if_shape_is_checked(self):
        with self.assertRaises(self.candidate.FormArityError):
            self.evaluate_special("if", [True])


if __name__ == "__main__":
    unittest.main()
