import unittest

from sprig import Evaluator, LanguageError, Symbol, default_environment, read_one
from sprig.runtime import structural_equal


class EvaluatorBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.env = default_environment()
        self.evaluator = Evaluator()

    def evaluate(self, source):
        return self.evaluator.evaluate(read_one(source), self.env)

    def assert_error(self, source, code):
        with self.assertRaises(LanguageError) as caught:
            self.evaluate(source)
        self.assertEqual(caught.exception.code, code)

    def test_truthiness_is_not_host_truthiness(self):
        for source in ("(if 0 1 2)", "(if () 1 2)", '(if "" 1 2)'):
            with self.subTest(source=source):
                self.assertEqual(self.evaluate(source), 1)
        self.assertIs(self.evaluate("(and)"), True)
        self.assertIsNone(self.evaluate("(or)"))
        self.assertIsNone(self.evaluate("(if nil 1)"))

    def test_special_form_validation_precedes_initializer_effects(self):
        self.evaluate("(def marker 0)")
        self.assert_error("(let ((x (set! marker 1)) malformed) x)", "EVAL_FORM")
        self.assertEqual(self.evaluate("marker"), 0)

    def test_sequential_bindings_and_multiple_body_forms(self):
        value = self.evaluate("(let ((x 2) (y (+ x 3))) (set! y (* y 2)) y)")
        self.assertEqual(value, 10)

    def test_closure_can_retain_mutable_binding(self):
        source = """
        (do
          (def counter
            (let ((n 0))
              (fn () (set! n (+ n 1)) n)))
          (list (counter) (counter) (counter)))
        """
        self.assertEqual(self.evaluate(source), [1, 2, 3])

    def test_callee_and_arguments_evaluate_left_to_right(self):
        source = """
        (do
          (def n 0)
          ((do (set! n (+ n 1)) +)
           (do (set! n (+ n 10)) n)
           (do (set! n (+ n 100)) n)))
        """
        self.assertEqual(self.evaluate(source), 122)
        self.assertEqual(self.evaluate("n"), 111)

    def test_assignment_never_creates_a_binding(self):
        self.assert_error("(set! nowhere 1)", "NAME_UNBOUND")

    def test_integer_division_is_exact_and_truncates_toward_zero(self):
        cases = {
            "(/ 17 3)": 5,
            "(/ -17 3)": -5,
            "(/ 17 -3)": -5,
            "(/ -17 -3)": 5,
            "(/ 100 6 4)": 4,
            "(/ 1000000000000000000000000000001 3)": 333333333333333333333333333333,
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(self.evaluate(source), expected)

    def test_builtin_arity_and_type_matrix(self):
        cases = [
            ("(-)", "BUILTIN_ARITY"),
            ("(/ 1)", "BUILTIN_ARITY"),
            ("(< 1)", "BUILTIN_ARITY"),
            ("(= 1)", "BUILTIN_ARITY"),
            ("(head 1)", "BUILTIN_TYPE"),
            ("(count nil)", "BUILTIN_TYPE"),
            ("(< 1 true)", "BUILTIN_TYPE"),
        ]
        for source, code in cases:
            with self.subTest(source=source):
                self.assert_error(source, code)

    def test_type_matrix(self):
        cases = {
            "nil": "nil", "true": "boolean", "1": "integer", '"x"': "string",
            "'x": "symbol", "()": "list", "+": "builtin", "(fn () 1)": "function",
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(self.evaluate("(type {0})".format(source)), Symbol(expected))

    def test_callable_equality_uses_identity(self):
        self.assertIs(self.evaluate("(= + +)"), True)
        self.assertIs(self.evaluate("(= (fn () 1) (fn () 1))"), False)
        self.assertFalse(structural_equal(Symbol("x"), "x"))
        self.assertFalse(structural_equal(True, 1))

    def test_zero_budgets_fail_deterministically_and_reset(self):
        evaluator = Evaluator(max_steps=0, max_call_depth=0)
        with self.assertRaises(LanguageError) as caught:
            evaluator.evaluate(1, self.env)
        self.assertEqual(caught.exception.code, "EVAL_STEP_LIMIT")
        evaluator = Evaluator(max_steps=100, max_call_depth=0)
        with self.assertRaises(LanguageError) as caught:
            evaluator.evaluate(read_one("((fn () 1))"), self.env)
        self.assertEqual(caught.exception.code, "EVAL_CALL_DEPTH")

    def test_malformed_special_forms(self):
        cases = [
            "(quote)", "(if true)", "(let () )", "(fn ())", "(def x)",
            "(set! 1 2)", "(fn (x x) x)", "(let ((x 1) (x 2)) x)",
        ]
        for source in cases:
            with self.subTest(source=source):
                self.assert_error(source, "EVAL_FORM")


if __name__ == "__main__":
    unittest.main()
