import unittest

from pebble import ArityError, CompileError, EvalError, Interpreter, read_one
from pebble.compiler import Compiler, Instruction, Program
from pebble.vm import VirtualMachine


class CompilerReferenceTests(unittest.TestCase):
    def setUp(self):
        self.interpreter = Interpreter(output=lambda _text: None)
        self.compiler = Compiler()
        self.vm = VirtualMachine(self.interpreter)

    def compare(self, source):
        form = read_one(source)
        interpreted = self.interpreter.eval(form)
        compiled = self.vm.run(self.compiler.compile(form))
        self.assertEqual(compiled, interpreted)

    def test_evaluator_and_vm_agree_on_supported_programs(self):
        for source in (
            "42",
            "'alpha",
            "'()",
            "(+)",
            "(+ 1 (* 2 3))",
            "(if false (/ 1 0) 9)",
            "(if true (do (+ 1 2) (list 3 4)) missing)",
            "(if nil 1)",
            "(= '(1 2) (list 1 2))",
        ):
            with self.subTest(source=source):
                self.compare(source)

    def test_compiler_rejects_state_and_closure_forms(self):
        for source in ("(def x 1)", "(let ((x 1)) x)", "(fn (x) x)"):
            with self.subTest(source=source), self.assertRaises(CompileError):
                self.compiler.compile(read_one(source))

    def test_compiler_validates_supported_special_form_arity(self):
        for source in ("(quote)", "(if true)", "(if true 1 2 3)"):
            with self.subTest(source=source), self.assertRaises(ArityError):
                self.compiler.compile(read_one(source))

    def test_vm_rejects_malformed_programs(self):
        programs = (
            Program((Instruction("RETURN"),), ()),
            Program((Instruction("CONST", 4), Instruction("RETURN")), (1,)),
            Program((Instruction("MYSTERY"),), ()),
            Program((Instruction("JUMP", 99),), ()),
            Program((Instruction("CALL", 0),), ()),
        )
        for program in programs:
            with self.subTest(program=program), self.assertRaises(EvalError):
                self.vm.run(program)

    def test_vm_rejects_user_function_calls_in_subset(self):
        self.interpreter.eval_source("(def f (fn () 1))")
        program = self.compiler.compile(read_one("(f)"))
        with self.assertRaisesRegex(EvalError, "limited to built-ins"):
            self.vm.run(program)


if __name__ == "__main__":
    unittest.main()
