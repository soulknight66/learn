import sys
import unittest

from pebble import ArityError, EvalError, Interpreter, NameResolutionError, Symbol, format_value


class InterpreterReferenceTests(unittest.TestCase):
    def setUp(self):
        self.emitted = []
        self.interpreter = Interpreter(output=self.emitted.append)

    def evaluate(self, source):
        return self.interpreter.eval_source(source)

    def test_empty_source_and_empty_do_return_nil(self):
        self.assertIsNone(self.evaluate("; nothing"))
        self.assertIsNone(self.evaluate("(do)"))

    def test_numeric_identities_and_minus_modes(self):
        self.assertEqual(self.evaluate("(+ )"), 0)
        self.assertEqual(self.evaluate("(*)"), 1)
        self.assertEqual(self.evaluate("(- 4)"), -4)
        self.assertEqual(self.evaluate("(- 10 3 2)"), 5)

    def test_division_truncates_toward_zero_for_all_signs(self):
        self.assertEqual(
            [self.evaluate(source) for source in ("(/ 7 3)", "(/ -7 3)", "(/ 7 -3)", "(/ -7 -3)")],
            [2, -2, -2, 2],
        )

    def test_comparisons_require_two_integers(self):
        self.assertEqual(
            self.evaluate("(list (< 1 2) (<= 2 2) (> 3 2) (>= 3 4))"),
            [True, True, True, False],
        )
        with self.assertRaises(EvalError):
            self.evaluate('(< "1" 2)')

    def test_equality_keeps_host_bool_and_int_distinct(self):
        self.assertFalse(self.evaluate("(= true 1)"))
        self.assertTrue(self.evaluate("(= '(1 (2)) '(1 (2)))"))
        self.assertFalse(self.evaluate("(= + +)"))
        self.assertFalse(self.evaluate("(= (fn () 1) (fn () 1))"))

    def test_only_false_and_nil_are_falsey(self):
        self.assertEqual(
            self.evaluate('(list (if false 1 2) (if nil 1 2) (if 0 3 4) (if "" 5 6) (if (list) 7 8))'),
            [2, 2, 3, 5, 7],
        )

    def test_unselected_if_branch_is_not_evaluated(self):
        self.assertEqual(self.evaluate("(if true 8 (/ 1 0))"), 8)
        self.assertEqual(self.evaluate("(if false missing 9)"), 9)

    def test_do_evaluates_left_to_right(self):
        self.assertEqual(self.evaluate("(do (def order 1) (def order 2) order)"), 2)

    def test_definition_inside_function_is_global(self):
        self.assertEqual(self.evaluate("((fn () (def planted 33)))"), 33)
        self.assertEqual(self.evaluate("planted"), 33)

    def test_special_form_name_is_reserved_only_in_operator_position(self):
        self.assertEqual(self.evaluate("(def if 99)"), 99)
        self.assertEqual(self.evaluate("if"), 99)
        self.assertEqual(self.evaluate("(if true 1 2)"), 1)

    def test_let_initializer_order_and_shadowing(self):
        self.evaluate("(def x 100)")
        self.assertEqual(self.evaluate("(let ((x 2) (y (+ x 5)) (x 9)) (list x y))"), [9, 7])
        self.assertEqual(self.evaluate("x"), 100)

    def test_closure_uses_definition_not_call_environment(self):
        source = """
        (def x 1)
        (def capture (fn () x))
        (let ((x 2)) (capture))
        """
        self.assertEqual(self.evaluate(source), 1)

    def test_multiple_function_body_forms(self):
        self.assertEqual(self.evaluate("((fn (x) (def side x) (+ x 1)) 8)"), 9)
        self.assertEqual(self.evaluate("side"), 8)

    def test_user_function_arity_and_parameter_shape(self):
        with self.assertRaises(ArityError):
            self.evaluate("((fn (x) x))")
        for source in ("(fn x x)", "(fn (x x) x)", "(fn (x))"):
            with self.subTest(source=source), self.assertRaises((EvalError, ArityError)):
                self.evaluate(source)

    def test_special_form_shape_errors_are_language_errors(self):
        sources = (
            "(quote)",
            "(if true)",
            "(def 1 2)",
            "(let x x)",
            "(let ((1 2)) 3)",
            "(fn 1 2)",
        )
        for source in sources:
            with self.subTest(source=source), self.assertRaises(EvalError):
                self.evaluate(source)

    def test_list_operations_and_nil_boundaries(self):
        self.assertEqual(self.evaluate("(list (first nil) (rest nil) (empty? nil) (count nil))"), [None, [], True, 0])
        self.assertEqual(self.evaluate("(list (first '(1 2)) (rest '(1 2)) (empty? '()) (count \"abc\"))"), [1, [2], True, 3])
        for source in ("(first 1)", "(rest true)", "(cons 1 2)", "(count false)"):
            with self.subTest(source=source), self.assertRaises(EvalError):
                self.evaluate(source)

    def test_string_builtins_distinguish_raw_and_printed_text(self):
        self.assertEqual(self.evaluate('(str "a" true nil "b")'), "atruenilb")
        self.assertEqual(self.evaluate('(pr-str "a\\nb")'), '"a\\nb"')

    def test_print_formats_once_and_returns_nil(self):
        self.assertIsNone(self.evaluate('(print "x\\ny")'))
        self.assertEqual(self.emitted, ['"x\\ny"'])

    def test_output_sink_failure_is_translated(self):
        def fail(_text):
            raise RuntimeError("host detail")

        interpreter = Interpreter(output=fail)
        with self.assertRaisesRegex(EvalError, "output sink failed"):
            interpreter.eval_source("(print 1)")

    def test_builtin_arity_type_and_zero_division_errors(self):
        for source, exception in (
            ("(-)", ArityError),
            ("(/ 1 2 3)", ArityError),
            ("(+ false)", EvalError),
            ("(/ 1 0)", EvalError),
            ("(1)", EvalError),
        ):
            with self.subTest(source=source), self.assertRaises(exception):
                self.evaluate(source)

    def test_name_resolution_error_is_stable(self):
        with self.assertRaisesRegex(NameResolutionError, "unbound symbol 'quartz'"):
            self.evaluate("quartz")

    def test_eval_rejects_non_language_host_objects(self):
        with self.assertRaises(EvalError):
            self.interpreter.eval(object())

    def test_tail_recursion_does_not_change_host_limit_or_grow_host_stack(self):
        before = sys.getrecursionlimit()
        source = """
        (def loop
          (fn (n acc)
            (if (= n 0)
                acc
                (loop (- n 1) (+ acc 1)))))
        (loop 6000 0)
        """
        self.assertEqual(self.evaluate(source), 6000)
        self.assertEqual(sys.getrecursionlimit(), before)

    def test_deep_runtime_data_printing_and_equality_are_iterative(self):
        source = """
        (def nest
          (fn (n value)
            (if (= n 0)
                value
                (nest (- n 1) (list value)))))
        (def deep (nest 1500 0))
        deep
        """
        value = self.evaluate(source)
        self.assertEqual(format_value(value), "(" * 1500 + "0" + ")" * 1500)
        self.assertTrue(self.evaluate("(= deep deep)"))

    def test_non_tail_host_stack_exhaustion_is_a_language_error(self):
        source = """
        (def non-tail
          (fn (n)
            (if (= n 0)
                0
                (+ 1 (non-tail (- n 1))))))
        (non-tail 2000)
        """
        with self.assertRaisesRegex(EvalError, "host recursion budget"):
            self.evaluate(source)

    def test_canonical_callable_formats(self):
        self.assertEqual(format_value(self.evaluate("+")), "<builtin:+>")
        self.assertEqual(format_value(self.evaluate("(fn () nil)")), "<fn>")
        self.assertEqual(format_value(Symbol("raw")), "raw")


if __name__ == "__main__":
    unittest.main()
