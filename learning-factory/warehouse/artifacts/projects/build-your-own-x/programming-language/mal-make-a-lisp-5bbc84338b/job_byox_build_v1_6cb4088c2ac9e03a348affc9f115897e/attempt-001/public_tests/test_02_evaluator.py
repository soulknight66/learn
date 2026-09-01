import unittest

from sprig import Evaluator, LanguageError, Symbol, default_environment, read_one


class EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.env = default_environment()
        self.evaluator = Evaluator()

    def evaluate(self, source):
        return self.evaluator.evaluate(read_one(source), self.env)

    def test_arithmetic_and_comparisons(self):
        self.assertEqual(self.evaluate("(+ 2 (* 3 4) (- 9 5))"), 18)
        self.assertEqual(self.evaluate("(/ -17 3)"), -5)
        self.assertIs(self.evaluate("(< 1 2 3)"), True)
        self.assertIs(self.evaluate("(< 1 3 2)"), False)

    def test_control_flow_short_circuits(self):
        self.assertEqual(self.evaluate("(if false (/ 1 0) 9)"), 9)
        self.assertEqual(self.evaluate("(and true 4 5)"), 5)
        self.assertEqual(self.evaluate("(or nil false \"yes\" (/ 1 0))"), "yes")
        self.assertEqual(self.evaluate("(do)"), None)

    def test_sequential_let_and_lists(self):
        result = self.evaluate("(let ((x 4) (y (+ x 3))) (cons x (list y)))")
        self.assertEqual(result, [4, 7])
        self.assertEqual(self.evaluate("(head ())"), None)
        self.assertEqual(self.evaluate("(tail ())"), [])

    def test_quote_type_and_structural_equality(self):
        self.assertEqual(self.evaluate("(type 'name)"), Symbol("symbol"))
        self.assertIs(self.evaluate("(= '(1 (2)) (list 1 (list 2)))"), True)
        self.assertIs(self.evaluate("(= 'word \"word\")"), False)

    def test_errors_are_language_errors(self):
        for source, code in [
            ("missing", "NAME_UNBOUND"),
            ("(1 2)", "EVAL_NOT_CALLABLE"),
            ("(+ 1 true)", "BUILTIN_TYPE"),
            ("(/ 1 0)", "BUILTIN_DIV_ZERO"),
            ("(if true)", "EVAL_FORM"),
        ]:
            with self.subTest(source=source):
                with self.assertRaises(LanguageError) as caught:
                    self.evaluate(source)
                self.assertEqual(caught.exception.code, code)


if __name__ == "__main__":
    unittest.main()
