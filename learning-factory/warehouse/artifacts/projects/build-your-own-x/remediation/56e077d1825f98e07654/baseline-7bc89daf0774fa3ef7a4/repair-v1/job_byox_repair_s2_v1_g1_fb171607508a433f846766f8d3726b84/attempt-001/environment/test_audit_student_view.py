import json
import unittest
from pathlib import Path

import audit_student_view as audit


class StudentViewPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = audit.load_policy(
            Path(__file__).with_name("student_view_policy.json")
        )

    def test_authoritative_allowlist(self):
        self.assertEqual(
            self.policy["root_files"],
            [
                "README.md",
                "AGENTS.md",
                "MANIFEST.yaml",
                "REQUIREMENTS.md",
                "CONCEPTS.md",
                "DESIGN_QUESTIONS.md",
            ],
        )
        self.assertEqual(
            self.policy["root_directories"],
            ["starter", "public_tests", "environment"],
        )

    def test_top_level_is_exact_in_materialized_mode(self):
        allowed = set(
            self.policy["root_files"] + self.policy["root_directories"]
        )
        audit.validate_top_level(allowed, self.policy, strict=True)
        with self.assertRaises(audit.AuditError):
            audit.validate_top_level(
                allowed | {"sealed"}, self.policy, strict=True
            )
        with self.assertRaises(audit.AuditError):
            audit.validate_top_level(
                allowed - {"starter"}, self.policy, strict=True
            )

    def test_forbidden_components_are_case_insensitive(self):
        audit.validate_relative_path("starter/kernel/main.c", self.policy)
        for relative in (
            "starter/sealed/key.c",
            "public_tests/Answers/review.md",
            "environment/reference_tests/test.c",
        ):
            with self.subTest(relative=relative):
                with self.assertRaises(audit.AuditError):
                    audit.validate_relative_path(relative, self.policy)

    def test_inventory_rejects_nonregular_entry(self):
        inventory = [
            {"path": name, "type": "regular_file", "sha256": "0" * 64}
            for name in self.policy["root_files"]
        ]
        inventory.extend(
            {"path": name, "type": "directory", "sha256": None}
            for name in self.policy["root_directories"]
        )
        audit.validate_inventory(inventory, self.policy)
        bad = json.loads(json.dumps(inventory))
        bad[-1]["type"] = "symbolic_link"
        with self.assertRaises(audit.AuditError):
            audit.validate_inventory(bad, self.policy)

    def test_inventory_digest_is_deterministic(self):
        inventory = [
            {
                "path": "README.md",
                "type": "regular_file",
                "sha256": "a" * 64,
            }
        ]
        self.assertEqual(
            audit.inventory_digest(inventory),
            audit.inventory_digest(list(inventory)),
        )


if __name__ == "__main__":
    unittest.main()
