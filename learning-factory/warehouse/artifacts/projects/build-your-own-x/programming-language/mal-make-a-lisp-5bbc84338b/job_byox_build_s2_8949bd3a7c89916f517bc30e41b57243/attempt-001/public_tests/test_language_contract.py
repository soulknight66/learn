import unittest

from pebble import (
    ArityError,
    EvalError,
    Interpreter,
    NameResolutionError,
    format_value,
)


class LanguageContractTests(unittest.TestCase):
    def setUp(self):
        self.output = []
        self.interpreter = Interpreter(output=self.output.append)

    def evaluate(self, source):
        return self.interpreter.eval_source(source)

    def test_arithmetic_and_truncating_division(self):
        self.assertEqual(self.evaluate("(+ 1 (* 2 5) (- 9 3))"), 17)
        self.assertEqual(self.evaluate("(/ -7 3)"), -2)

    def test_falsey_values_and_lazy_if(self):
        self.assertEqual(self.evaluate("(if 0 10 missing)"), 10)
        self.assertEqual(self.evaluate("(if nil missing 20)"), 20)
        self.assertIsNone(self.evaluate("(if false 1)"))

    def test_let_is_sequential_and_lexical(self):
        self.assertEqual(self.evaluate("(let ((x 4) (y (+ x 3))) (* x y))"), 28)
        with self.assertRaises(NameResolutionError):
            self.evaluate("x")

    def test_closure_survives_creating_call(self):
        source = """
        (def make-adder (fn (x) (fn (y) (+ x y))))
        (def add-nine (make-adder 9))
        (add-nine 6)
        """
        self.assertEqual(self.evaluate(source), 15)

    def test_global_state_persists_across_sources(self):
        self.assertEqual(self.evaluate("(def marker 41)"), 41)
        self.assertEqual(self.evaluate("(+ marker 1)"), 42)

    def test_list_builtins_do_not_mutate_inputs(self):
        self.evaluate("(def xs (list 2 3))")
        self.assertEqual(self.evaluate("(cons 1 xs)"), [1, 2, 3])
        self.assertEqual(self.evaluate("xs"), [2, 3])
        self.assertEqual(self.evaluate("(rest xs)"), [3])

    def test_print_uses_configured_sink(self):
        self.assertIsNone(self.evaluate('(print (list 1 "rock"))'))
        self.assertEqual(self.output, ['(1 "rock")'])

    def test_canonical_format(self):
        value = self.evaluate("(list true false nil 'name \"a\\nb\")")
        self.assertEqual(format_value(value), '(true false nil name "a\\nb")')

    def test_language_error_types(self):
        with self.assertRaises(ArityError):
            self.evaluate("(/ 1)")
        with self.assertRaises(EvalError):
            self.evaluate("(+ true 1)")
        with self.assertRaises(EvalError):
            self.evaluate("(1 2)")

    def test_tail_recursive_loop(self):
        source = """
        (def sum-down
          (fn (n acc)
            (if (= n 0)
                acc
                (sum-down (- n 1) (+ acc n)))))
        (sum-down 750 0)
        """
        self.assertEqual(self.evaluate(source), 281625)


if __name__ == "__main__":
    unittest.main()
