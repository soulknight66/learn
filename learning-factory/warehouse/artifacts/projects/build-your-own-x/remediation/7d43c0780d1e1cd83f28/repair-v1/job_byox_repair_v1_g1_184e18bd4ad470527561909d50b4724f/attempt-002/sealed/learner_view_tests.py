"""Deterministic tests for the learner-view isolation policy."""

import importlib.util
import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / 'environment' / 'export-learner-view.py'
SPEC = importlib.util.spec_from_file_location('learner_view_exporter', str(SCRIPT))
EXPORTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORTER)


class LearnerViewPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = EXPORTER.load_policy()
        cls.records = EXPORTER.collect_files(ROOT, cls.policy['allowed_files'])

    def test_receipt_is_exact_and_repeatable(self):
        first = EXPORTER.receipt(self.policy, self.records)
        second = EXPORTER.receipt(self.policy, self.records)
        self.assertEqual(first, second)
        self.assertEqual(first, {
            'digest_algorithm': 'learner-view-sha256-v1',
            'file_count': 23,
            'sha256': 'd1fb33d5b341307feb163c8cdab32aeea7c7725de2269ddd2887b1ead964822d',
        })

    def test_allowlist_cannot_reach_denied_prefixes(self):
        for relative in self.policy['allowed_files']:
            for prefix in self.policy['denied_prefixes']:
                self.assertFalse(
                    EXPORTER.denied(relative, prefix),
                    '{} unexpectedly reaches {}'.format(relative, prefix),
                )

    def test_solution_bearing_components_are_rejected(self):
        for relative in (
            'sealed/reference/src/index.js',
            'starter/solution/index.js',
            'public_tests/hidden_tests/case.js',
            'environment/answers/result.txt',
        ):
            with self.assertRaises(EXPORTER.PolicyError):
                EXPORTER.validate_relative_path(relative)

    def test_export_refuses_the_production_root_without_writing(self):
        destination = ROOT / 'learner-view-test-must-not-exist'
        self.assertFalse(os.path.lexists(str(destination)))
        with self.assertRaisesRegex(EXPORTER.PolicyError, 'outside the production pack'):
            EXPORTER.export_view(str(destination), self.policy, self.records)
        self.assertFalse(os.path.lexists(str(destination)))


if __name__ == '__main__':
    unittest.main()
