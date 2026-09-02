import json
import tempfile
import unittest
from pathlib import Path

import audit_student_view as audit
import materialize_student_view as materializer


def regular(path: str) -> dict[str, object]:
    return {"path": path, "type": "regular_file", "sha256": "0" * 64}


def directory(path: str) -> dict[str, object]:
    return {"path": path, "type": "directory", "sha256": None}


class StudentViewPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        policy_dir = Path(__file__).parent
        cls.initial = audit.load_policy(policy_dir / "student_view_policy.json")
        cls.post_attempt = audit.load_policy(
            policy_dir / "post_attempt_view_policy.json"
        )

    def test_initial_view_includes_license_boundary(self):
        self.assertEqual(self.initial["stage"], "initial")
        self.assertIn("LICENSE_BOUNDARY.md", self.initial["root_files"])
        self.assertEqual(
            self.initial["recursive_directories"],
            ["starter", "public_tests", "environment"],
        )
        self.assertEqual(self.initial["selected_files"], [])
        self.assertEqual(self.initial["selected_directories"], [])

    def test_post_attempt_view_selects_only_unsolved_exercises(self):
        self.assertEqual(self.post_attempt["stage"], "post-attempt-exercises")
        self.assertIn("LICENSE_BOUNDARY.md", self.post_attempt["root_files"])
        self.assertEqual(
            self.post_attempt["selected_files"],
            [
                "debugging/README.md",
                "debugging/scheduler-stall/README.md",
                "debugging/scheduler-stall/fixture.c",
                "review_exercises/README.md",
                "review_exercises/vm-boundary/README.md",
                "review_exercises/vm-boundary/candidate.c",
            ],
        )
        selected = (
            self.post_attempt["selected_files"]
            + self.post_attempt["selected_directories"]
        )
        self.assertFalse(any("sealed" in Path(item).parts for item in selected))

    def test_top_level_is_exact_in_materialized_mode(self):
        allowed = set(self.initial["root_files"] + self.initial["recursive_directories"])
        audit.validate_top_level(allowed, self.initial, strict=True)
        with self.assertRaises(audit.AuditError):
            audit.validate_top_level(allowed | {"sealed"}, self.initial, strict=True)
        with self.assertRaises(audit.AuditError):
            audit.validate_top_level(allowed - {"starter"}, self.initial, strict=True)

    def test_forbidden_components_are_case_insensitive(self):
        audit.validate_relative_path("starter/kernel/main.c", self.initial)
        for relative in (
            "starter/sealed/key.c",
            "public_tests/Answers/review.md",
            "environment/reference_tests/test.c",
        ):
            with self.subTest(relative=relative):
                with self.assertRaises(audit.AuditError):
                    audit.validate_relative_path(relative, self.initial)

    def test_post_attempt_inventory_rejects_nested_answer(self):
        inventory = [regular(name) for name in self.post_attempt["root_files"]]
        inventory.extend(
            directory(name) for name in self.post_attempt["recursive_directories"]
        )
        inventory.extend(
            directory(name) for name in self.post_attempt["selected_directories"]
        )
        inventory.extend(regular(name) for name in self.post_attempt["selected_files"])
        audit.validate_inventory(inventory, self.post_attempt)
        inventory.append(directory("debugging/scheduler-stall/sealed"))
        with self.assertRaises(audit.AuditError):
            audit.validate_inventory(inventory, self.post_attempt)

    def test_inventory_rejects_nonregular_entry(self):
        inventory = [regular(name) for name in self.initial["root_files"]]
        inventory.extend(
            directory(name) for name in self.initial["recursive_directories"]
        )
        audit.validate_inventory(inventory, self.initial)
        bad = json.loads(json.dumps(inventory))
        bad[-1]["type"] = "symbolic_link"
        with self.assertRaises(audit.AuditError):
            audit.validate_inventory(bad, self.initial)

    def test_inventory_digest_is_deterministic(self):
        inventory = [regular("README.md")]
        self.assertEqual(
            audit.inventory_digest(inventory),
            audit.inventory_digest(list(inventory)),
        )

    def test_materializer_excludes_unselected_sealed_answer_and_self_audits(self):
        policy = {
            "schema_version": 2,
            "stage": "synthetic-post-attempt",
            "exposure_model": "recursive-roots-with-exact-additions",
            "root_files": ["NOTICE"],
            "recursive_directories": ["base"],
            "selected_files": ["exercise/README.md", "exercise/demo/fixture.c"],
            "selected_directories": ["exercise", "exercise/demo"],
            "forbidden_path_components": [
                "sealed",
                "reference",
                "reference_tests",
                "hidden_tests",
                "solution",
                "solutions",
                "answers",
            ],
            "allowed_entry_types": ["directory", "regular_file"],
            "independent_materialization_validation": "REQUIRED",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / "NOTICE").write_text("notice\n", encoding="utf-8")
            (source / "base").mkdir()
            (source / "base" / "task.txt").write_text("task\n", encoding="utf-8")
            (source / "exercise" / "demo" / "sealed").mkdir(parents=True)
            (source / "exercise" / "README.md").write_text(
                "exercise\n", encoding="utf-8"
            )
            (source / "exercise" / "demo" / "fixture.c").write_text(
                "int fixture;\n", encoding="utf-8"
            )
            (source / "exercise" / "demo" / "sealed" / "ANSWER.md").write_text(
                "answer\n", encoding="utf-8"
            )
            policy_path = root / "policy.json"
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            destination = root / "view"

            result = materializer.materialize(source, destination, policy_path)

            loaded = audit.load_policy(policy_path)
            strict_inventory = audit.scan(destination, loaded, strict=True)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(
                result["inventory_sha256"], audit.inventory_digest(strict_inventory)
            )
            self.assertFalse((destination / "exercise" / "demo" / "sealed").exists())


if __name__ == "__main__":
    unittest.main()
