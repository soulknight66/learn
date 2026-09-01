#!/usr/bin/env python3
"""Static unit coverage for the harness-controlled module-under-test binding."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
BINDING = ROOT / "sealed" / "evaluator" / "bindings.mjs"
RUNNERS = (
    ROOT / "sealed" / "adversarial" / "run.mjs",
    ROOT / "sealed" / "benchmarks" / "benchmark.mjs",
)


class EvaluatorWiringTests(unittest.TestCase):
    def test_binding_uses_fixed_pack_relative_entries(self):
        text = BINDING.read_text(encoding="utf-8")
        self.assertIn('const CANDIDATE_ROOT = resolve(PACK_ROOT, "starter")', text)
        self.assertIn('const ORACLE_ROOT = resolve(PACK_ROOT, "sealed/reference")', text)
        self.assertIn('const CANDIDATE_ENTRY = resolve(CANDIDATE_ROOT, "src/index.js")', text)
        self.assertIn('const ORACLE_ENTRY = resolve(ORACLE_ROOT, "index.js")', text)
        self.assertNotIn("process.argv", text)
        self.assertNotIn("process.env", text)

    def test_evaluator_runners_do_not_bypass_the_binding(self):
        for runner in RUNNERS:
            text = runner.read_text(encoding="utf-8")
            self.assertIn('from "../evaluator/bindings.mjs"', text, str(runner))
            self.assertNotIn('from "../reference/index.js"', text, str(runner))
            self.assertNotIn("starter/src/index.js", text, str(runner))

    def test_supplied_candidate_imports_stay_inside_starter(self):
        starter = ROOT / "starter"
        from_pattern = re.compile(r"\bfrom\s*[\"']([^\"']+)[\"']")
        side_effect_pattern = re.compile(r"\bimport\s*[\"']([^\"']+)[\"']")
        for source_path in sorted((starter / "src").glob("*.js")):
            text = source_path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"\bimport\s*\(")
            specifiers = from_pattern.findall(text) + side_effect_pattern.findall(text)
            for specifier in specifiers:
                self.assertTrue(specifier.startswith("."), (source_path, specifier))
                target = (source_path.parent / specifier).resolve()
                target.relative_to(starter.resolve())
                self.assertTrue(target.is_file(), (source_path, specifier))

    def test_binding_records_candidate_and_oracle_identities(self):
        text = BINDING.read_text(encoding="utf-8")
        self.assertIn('algorithm: "path-content-sha256-v1"', text)
        self.assertIn('treeIdentity("candidate", CANDIDATE_ROOT, CANDIDATE_ENTRY)', text)
        self.assertIn('treeIdentity("oracle", ORACLE_ROOT, ORACLE_ENTRY)', text)
        self.assertIn("before.candidate.sha256 !== after.candidate.sha256", text)
        self.assertLess(text.index("reportArtifacts(before)"), text.index("await Promise.all"))


if __name__ == "__main__":
    unittest.main()
