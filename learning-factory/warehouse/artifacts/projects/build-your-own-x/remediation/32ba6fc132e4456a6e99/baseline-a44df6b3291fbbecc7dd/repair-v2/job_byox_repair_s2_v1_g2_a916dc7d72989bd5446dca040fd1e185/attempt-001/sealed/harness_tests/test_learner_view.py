"""Deterministic regressions for the learner-view allowlist and projector."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


REPOSITORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY))

from environment.process_runner import build_directory
from environment.project_learner_view import (
    EXPECTED_POLICY,
    create_projection,
    load_policy,
    source_inventory,
)


class LearnerViewTest(unittest.TestCase):
    def test_repository_policy_inventories_only_allowlisted_roots(self) -> None:
        policy = load_policy(REPOSITORY)
        self.assertEqual(EXPECTED_POLICY, policy)
        inventory = source_inventory(REPOSITORY, policy)
        inventoried_roots = {
            relative.rstrip("/").split("/", maxsplit=1)[0] for relative in inventory
        }
        self.assertEqual(set(policy["included_top_level"]), inventoried_roots)
        self.assertTrue(
            set(policy["excluded_top_level"]).isdisjoint(inventoried_roots)
        )

    def test_synthetic_projection_omits_evaluator_roots(self) -> None:
        with build_directory(
            REPOSITORY, "minilog-view-test-", requested_root=None
        ) as temporary:
            source = temporary / "source"
            source.mkdir()
            directory_names = {"starter", "public_tests", "environment"}
            directory_names.update(
                name for name in EXPECTED_POLICY["excluded_top_level"] if "." not in name
            )
            for name in directory_names:
                (source / name).mkdir()
            for name in EXPECTED_POLICY["included_top_level"]:
                if name not in directory_names:
                    (source / name).write_text(f"allowed:{name}\n", encoding="utf-8")
            for name in EXPECTED_POLICY["excluded_top_level"]:
                if name not in directory_names:
                    (source / name).write_text(f"evaluator:{name}\n", encoding="utf-8")
            (source / "starter" / "Example.java").write_text(
                "final class Example {}\n", encoding="utf-8"
            )
            (source / "sealed" / "ANSWER.md").write_text(
                "synthetic evaluator-only marker\n", encoding="utf-8"
            )

            expected = source_inventory(source, EXPECTED_POLICY)
            destination = temporary / "projection"
            create_projection(source, destination, EXPECTED_POLICY, expected)

            self.assertEqual(
                set(EXPECTED_POLICY["included_top_level"]),
                {path.name for path in destination.iterdir()},
            )
            self.assertTrue((destination / "starter" / "Example.java").is_file())
            for name in EXPECTED_POLICY["excluded_top_level"]:
                self.assertFalse((destination / name).exists())
            self.assertFalse(any(path.name == "ANSWER.md" for path in destination.rglob("*")))
            self.assertTrue((source / "sealed" / "ANSWER.md").is_file())


if __name__ == "__main__":
    unittest.main()
