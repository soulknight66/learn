import unittest

from sprig import Evaluator, LanguageError, default_environment, read_one


class FunctionTests(unittest.TestCase):
    def setUp(self):
        self.env = default_environment()
        self.evaluator = Evaluator(max_steps=10000, max_call_depth=200)

    def evaluate(self, source):
        return self.evaluator.evaluate(read_one(source), self.env)

    def test_closure_captures_lexical_environment(self):
        source = """
        (do
          (def make-adder (fn (x) (fn (y) (+ x y))))
          (def add-seven (make-adder 7))
          (let ((x 100)) (add-seven 5)))
        """
        self.assertEqual(self.evaluate(source), 12)

    def test_mutation_targets_nearest_existing_scope(self):
        source = """
        (do
          (def x 1)
          (let ((x 10)) (set! x 11) x)
          x)
        """
        self.assertEqual(self.evaluate(source), 1)

    def test_recursion(self):
        source = """
        (do
          (def fact (fn (n) (if (= n 0) 1 (* n (fact (- n 1))))))
          (fact 6))
        """
        self.assertEqual(self.evaluate(source), 720)

    def test_function_arity_and_duplicate_parameters(self):
        for source in ["((fn (x) x))", "(fn (x x) x)"]:
            with self.subTest(source=source):
                with self.assertRaises(LanguageError) as caught:
                    self.evaluate(source)
                self.assertIn(caught.exception.code, ("EVAL_ARITY", "EVAL_FORM"))

    def test_step_and_call_depth_limits_reset_per_evaluation(self):
        limited = Evaluator(max_steps=60, max_call_depth=5)
        limited.evaluate(
            read_one("(def loop (fn (n) (if (= n 0) 0 (loop (- n 1)))))"), self.env
        )
        with self.assertRaises(LanguageError) as caught:
            limited.evaluate(read_one("(loop 20)"), self.env)
        self.assertIn(caught.exception.code, ("EVAL_CALL_DEPTH", "EVAL_STEP_LIMIT"))
        self.assertEqual(limited.evaluate(read_one("(+ 1 2)"), self.env), 3)


if __name__ == "__main__":
    unittest.main()
