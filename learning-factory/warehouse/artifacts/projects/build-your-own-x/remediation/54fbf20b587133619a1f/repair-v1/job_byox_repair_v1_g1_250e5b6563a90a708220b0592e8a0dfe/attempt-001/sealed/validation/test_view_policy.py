#!/usr/bin/env python3
"""Deterministic tests for learner-view projection without creating a view."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from view_policy import BASE, STAGES, audit_views


class ViewPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audits = audit_views()

    def test_stage_names_and_roots_are_cumulative(self):
        self.assertEqual([item["name"] for item in self.audits], [name for name, _ in STAGES])
        expected_roots = list(BASE)
        previous_paths = set()
        for audit, (_, additions) in zip(self.audits, STAGES):
            expected_roots.extend(additions)
            self.assertEqual(audit["roots"], expected_roots)
            self.assertTrue(previous_paths.issubset(set(audit["paths"])))
            previous_paths = set(audit["paths"])

    def test_no_view_exposes_sealed_or_administrator_files(self):
        forbidden = {"sealed", "VALIDATION.md", "PROVENANCE.json", "LICENSE_BOUNDARY.md"}
        for audit in self.audits:
            top_levels = {path.split("/", 1)[0] for path in audit["paths"]}
            self.assertTrue(forbidden.isdisjoint(top_levels), audit["name"])

    def test_later_prompts_are_absent_until_revealed(self):
        additions = [root for _, roots in STAGES for root in roots]
        revealed = set(BASE)
        for audit, (_, roots) in zip(self.audits, STAGES):
            revealed.update(roots)
            top_levels = {path.split("/", 1)[0] for path in audit["paths"]}
            self.assertTrue((set(additions) - revealed).isdisjoint(top_levels), audit["name"])

    def test_each_view_has_a_bound_identity(self):
        for audit in self.audits:
            self.assertEqual(audit["algorithm"], "path-content-sha256-v1")
            self.assertRegex(audit["sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(audit["files"], len(audit["paths"]))


if __name__ == "__main__":
    unittest.main()
