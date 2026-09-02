from __future__ import annotations

import unittest
from pathlib import Path

from environment.export_student_view import build_plan


class StudentViewBoundaryTests(unittest.TestCase):
    def test_checked_plan_contains_only_learner_roots(self) -> None:
        pack = Path(__file__).resolve().parents[2]
        paths = tuple(relative.as_posix() for relative, _ in build_plan(pack))
        self.assertIn("starter/pydocklet/engine.py", paths)
        self.assertIn("public_tests/test_engine.py", paths)
        self.assertIn("environment/COPYING_NOTICE.md", paths)
        self.assertIn("environment/student_view_allowlist.json", paths)
        evaluator_roots = {
            "PROVENANCE.json",
            "LICENSE_BOUNDARY.md",
            "VALIDATION.md",
            "adversarial",
            "benchmarks",
            "debugging",
            "review_exercises",
            "sealed",
        }
        self.assertFalse(evaluator_roots.intersection(path.split("/", 1)[0] for path in paths))

    def test_learner_view_carries_generated_material_terms(self) -> None:
        pack = Path(__file__).resolve().parents[2]
        notice = (pack / "environment" / "COPYING_NOTICE.md").read_text(encoding="utf-8")
        self.assertIn("permission is granted", notice)
        self.assertIn("NOASSERTION", notice)
        self.assertIn("Preserve this notice", notice)


if __name__ == "__main__":
    unittest.main()
