from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
BIN = ROOT / "sealed" / "reference" / "build" / "emberc-ref"
TOWER = ROOT / "sealed" / "reference" / "self" / "tower.ec"


def run_ref(*arguments: str, timeout: float = 3.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(BIN), *arguments],
        cwd=ROOT,
        text=True,
        input="",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


class ReferenceBehaviorTests(unittest.TestCase):
    def run_source(self, source: str, *guest_args: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="ember-private-") as directory:
            path = Path(directory) / "case.ec"
            path.write_text(source, encoding="ascii")
            arguments = [str(path)]
            if guest_args:
                arguments.extend(["--", *guest_args])
            return run_ref(*arguments)

    def test_all_arithmetic_and_comparisons(self) -> None:
        result = run_ref(str(ROOT / "sealed/reference_tests/cases/all_ops.ec"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "13\n7\n30\n3\n1\n1\n1\n1\n1\n1\n1\n0\n",
        )

    def test_shadow_initializer_sees_outer_name(self) -> None:
        result = self.run_source(
            "int main(){ int x=5; { int x=x+1; print(x); } print(x); }"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "6\n5\n")

    def test_dangling_else_binds_nearest_if(self) -> None:
        result = self.run_source(
            "int main(){ if(1) if(0) print(1); else print(2); return 0; }"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "2\n")

    def test_sequential_scopes_reuse_slots(self) -> None:
        blocks = "".join("{ int x=%d; }" % index for index in range(400))
        result = self.run_source("int main(){" + blocks + "return 0;}")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_too_many_simultaneous_locals(self) -> None:
        declarations = "".join("int x%d=%d;" % (index, index) for index in range(257))
        result = self.run_source("int main(){" + declarations + "return 0;}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("active local", result.stderr)

    def test_checked_minimum_division(self) -> None:
        result = self.run_source(
            "int main(){ int x=-9223372036854775807-1; print(x/-1); }"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("overflow", result.stderr)

    def test_heap_edges(self) -> None:
        result = self.run_source(
            "int main(){ store(0,11); store(4095,31); "
            "print(load(0)+load(4095)); return 0; }"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "42\n")
        invalid = self.run_source("int main(){ print(load(4096)); }")
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("invalid heap index", invalid.stderr)

    def test_instruction_budget(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ember-budget-") as directory:
            path = Path(directory) / "loop.ec"
            path.write_text("int main(){ while(1) { } }", encoding="ascii")
            result = run_ref("--max-steps", "20", str(path))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("instruction budget exceeded", result.stderr)

    def test_literal_and_identifier_limits(self) -> None:
        literal = self.run_source("int main(){ print(9223372036854775808); }")
        self.assertNotEqual(literal.returncode, 0)
        self.assertIn("INT64_MAX", literal.stderr)
        name = "a" * 64
        identifier = self.run_source("int main(){ int " + name + "; }")
        self.assertNotEqual(identifier.returncode, 0)
        self.assertIn("identifier exceeds", identifier.stderr)

    def test_emit_has_documented_word_layout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ember-emit-") as directory:
            source = Path(directory) / "small.ec"
            output = Path(directory) / "small.bc"
            source.write_text("int main(){ print(3); return 0; }", encoding="ascii")
            result = run_ref("--emit", str(source), str(output))
            self.assertEqual(result.returncode, 0, result.stderr)
            words = [int(line) for line in output.read_text().splitlines()]
        self.assertEqual(words, [1, 3, 19, 1, 0, 24, 1, 0, 24])

    def test_tower_executes_own_bytecode(self) -> None:
        result = run_ref("--tower", str(TOWER), timeout=5.0)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "4242\n")


if __name__ == "__main__":
    unittest.main()
