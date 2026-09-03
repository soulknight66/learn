import importlib.util
import os
import sys
import unittest

sys.dont_write_bytecode = True


PACK_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODULE_PATH = os.path.join(PACK_ROOT, "environment", "learner_view.py")
SPEC = importlib.util.spec_from_file_location("learner_view", MODULE_PATH)
LEARNER_VIEW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LEARNER_VIEW)


class LearnerViewTests(unittest.TestCase):
    def test_source_selection_is_limited_to_the_authoritative_allowlist(self):
        inventory = LEARNER_VIEW.source_inventory(PACK_ROOT)
        selected_roots = {path.split("/", 1)[0] for path in inventory}
        self.assertEqual(selected_roots, set(LEARNER_VIEW.LEARNER_ROOTS))

        evaluator_roots = {
            "sealed",
            "adversarial",
            "debugging",
            "review_exercises",
            "benchmarks",
            "PROVENANCE.json",
            "LICENSE_BOUNDARY.md",
            "VALIDATION.md",
        }
        self.assertTrue(selected_roots.isdisjoint(evaluator_roots))
        self.assertIn("starter/index.js", inventory)
        self.assertIn("public_tests/framework.test.js", inventory)
        self.assertIn("environment/learner_view.py", inventory)
        self.assertEqual(
            {path for path in inventory if path.startswith("environment")},
            {
                "environment",
                "environment/README.md",
                "environment/learner_view.py",
            },
        )
        self.assertNotIn("environment/verify_artifact.py", inventory)

    def test_exact_comparison_rejects_an_extra_evaluator_path(self):
        expected = {
            "README.md": {"type": "file", "sha256": "expected"},
        }
        observed = dict(expected)
        observed["sealed/reference/index.js"] = {
            "type": "file",
            "sha256": "unexpected",
        }
        with self.assertRaisesRegex(LEARNER_VIEW.ProjectionError, "extra=sealed/"):
            LEARNER_VIEW.compare_inventories(expected, observed)

    def test_exact_comparison_rejects_changed_learner_content(self):
        expected = {
            "README.md": {"type": "file", "sha256": "expected"},
        }
        observed = {
            "README.md": {"type": "file", "sha256": "changed"},
        }
        with self.assertRaisesRegex(LEARNER_VIEW.ProjectionError, "changed=README.md"):
            LEARNER_VIEW.compare_inventories(expected, observed)


if __name__ == "__main__":
    unittest.main()
