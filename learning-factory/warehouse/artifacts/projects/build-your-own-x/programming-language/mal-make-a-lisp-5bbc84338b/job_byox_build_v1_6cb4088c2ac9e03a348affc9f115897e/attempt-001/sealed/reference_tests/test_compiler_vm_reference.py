import unittest

from sprig import (
    Bytecode, Compiler, Evaluator, LanguageError, VirtualMachine,
    default_environment, read_one,
)


class CompilerVmBoundaryTests(unittest.TestCase):
    def test_value_matrix_matches_tree_walker(self):
        expressions = [
            "nil", "true", "false", "-3", '"hello"', "()", "'symbol", "'(1 (2 3))",
            "(+)", "(*)", "(- 10 3 2)", "(/ 81 3 3)", "(>= 4 4 2)",
            "(if nil 1)", "(if () (do 1 2 3) 4)",
            "((if true + -) 9 4)", "(head (list 7 8))",
        ]
        for source in expressions:
            with self.subTest(source=source):
                form = read_one(source)
                expected = Evaluator().evaluate(form, default_environment())
                actual = VirtualMachine().run(Compiler().compile(form), default_environment())
                self.assertEqual(actual, expected)

    def test_documented_runtime_errors_match(self):
        for source, code in [("(/ 1 0)", "BUILTIN_DIV_ZERO"), ("unknown", "NAME_UNBOUND")]:
            with self.subTest(source=source):
                form = read_one(source)
                for action in (
                    lambda: Evaluator().evaluate(form, default_environment()),
                    lambda: VirtualMachine().run(Compiler().compile(form), default_environment()),
                ):
                    with self.assertRaises(LanguageError) as caught:
                        action()
                    self.assertEqual(caught.exception.code, code)

    def test_every_excluded_special_form_is_rejected(self):
        sources = [
            "(def x 1)", "(set! x 1)", "(let ((x 1)) x)", "(fn (x) x)",
            "(and true true)", "(or false true)",
        ]
        for source in sources:
            with self.subTest(source=source):
                with self.assertRaises(LanguageError) as caught:
                    Compiler().compile(read_one(source))
                self.assertEqual(caught.exception.code, "COMPILE_UNSUPPORTED")

    def test_malformed_compiler_forms(self):
        for source in ("(quote)", "(if true)", "(if true 1 2 3)"):
            with self.subTest(source=source):
                with self.assertRaises(LanguageError) as caught:
                    Compiler().compile(read_one(source))
                self.assertEqual(caught.exception.code, "COMPILE_FORM")

    def test_compiler_instance_resets_between_programs(self):
        compiler = Compiler()
        first = compiler.compile(read_one("(+ 1 2)"))
        second = compiler.compile(read_one("9"))
        self.assertGreater(len(first.instructions), len(second.instructions))
        self.assertEqual(second.instructions, [("CONST", 0), ("RETURN",)])
        self.assertEqual(second.constants, [9])

    def test_vm_malformed_instruction_matrix(self):
        programs = [
            Bytecode([], []),
            Bytecode([None], []),
            Bytecode([("NOPE",)], []),
            Bytecode([("CONST", 2), ("RETURN",)], [1]),
            Bytecode([("LOAD", 2), ("RETURN",)], []),
            Bytecode([("POP",), ("RETURN",)], []),
            Bytecode([("JUMP", 2)], []),
            Bytecode([("JUMP_IF_FALSE", 0)], []),
            Bytecode([("CALL", -1)], []),
            Bytecode([("RETURN",)], []),
            Bytecode([("CONST", 0), ("CONST", 0), ("RETURN",)], [1]),
        ]
        for index, bytecode in enumerate(programs):
            with self.subTest(index=index):
                with self.assertRaises(LanguageError) as caught:
                    VirtualMachine(max_steps=20).run(bytecode)
                self.assertTrue(caught.exception.code.startswith("VM_"))

    def test_vm_only_invokes_builtins(self):
        env = default_environment()
        closure = Evaluator().evaluate(read_one("(fn (x) x)"), env)
        env.define("identity", closure)
        bytecode = Compiler().compile(read_one("(identity 4)"))
        with self.assertRaises(LanguageError) as caught:
            VirtualMachine().run(bytecode, env)
        self.assertEqual(caught.exception.code, "VM_NOT_CALLABLE")

    def test_disassembly_does_not_crash_on_malformed_constants(self):
        listing = Bytecode([("CONST", 99), (), None], []).disassemble()
        self.assertIn("CONST 99", listing)
        self.assertEqual(len(listing.splitlines()), 3)


if __name__ == "__main__":
    unittest.main()
