import unittest

from sprig import (
    Bytecode, Compiler, Evaluator, LanguageError, VirtualMachine,
    default_environment, read_one,
)


class CompilerVmTests(unittest.TestCase):
    def compare_engines(self, source):
        form = read_one(source)
        interpreted = Evaluator().evaluate(form, default_environment())
        compiled = Compiler().compile(form)
        executed = VirtualMachine().run(compiled, default_environment())
        self.assertEqual(executed, interpreted)

    def test_supported_subset_matches_evaluator(self):
        for source in [
            "42",
            "'((one) 2)",
            "(+ 1 (* 2 3))",
            "(if (< 2 3) (do 8 9) (/ 1 0))",
            "()",
        ]:
            with self.subTest(source=source):
                self.compare_engines(source)

    def test_disassembly_is_stable_and_has_return(self):
        bytecode = Compiler().compile(read_one("(+ 1 2)"))
        listing = bytecode.disassemble()
        self.assertIn("LOAD +", listing)
        self.assertIn("CALL 2", listing)
        self.assertTrue(listing.rstrip().endswith("RETURN"))

    def test_unsupported_form_is_explicit(self):
        with self.assertRaises(LanguageError) as caught:
            Compiler().compile(read_one("(let ((x 1)) x)"))
        self.assertEqual(caught.exception.code, "COMPILE_UNSUPPORTED")

    def test_vm_rejects_malformed_code_without_host_exception(self):
        malformed = Bytecode([("CALL", 1), ("RETURN",)], [])
        with self.assertRaises(LanguageError) as caught:
            VirtualMachine().run(malformed)
        self.assertTrue(caught.exception.code.startswith("VM_"))

    def test_vm_step_limit(self):
        bytecode = Bytecode([("JUMP", 0)], [])
        with self.assertRaises(LanguageError) as caught:
            VirtualMachine(max_steps=5).run(bytecode)
        self.assertEqual(caught.exception.code, "VM_STEP_LIMIT")


if __name__ == "__main__":
    unittest.main()
