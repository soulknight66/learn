import hashlib
import json
import os
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]

REQUIRED = (
    "README.md",
    "AGENTS.md",
    "MANIFEST.yaml",
    "PROVENANCE.json",
    "LICENSE_BOUNDARY.md",
    "REQUIREMENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
    "VALIDATION.md",
    "starter/README.md",
    "public_tests/README.md",
    "environment/README.md",
    "sealed/reference/README.md",
    "sealed/reference_tests/README.md",
    "sealed/DESIGN.md",
    "sealed/TRADEOFFS.md",
    "sealed/REVIEW.md",
    "sealed/alternatives/README.md",
    "sealed/production/PRODUCTIONIZATION.md",
    "adversarial/README.md",
    "debugging/README.md",
    "review_exercises/README.md",
    "benchmarks/README.md",
)

FORBIDDEN = (
    ".git",
    ".env",
    ".venv",
    "credentials.json",
    "secrets",
    "reference",
    "reference_tests",
    "hidden_tests",
    "solution",
    "solutions",
    "answers",
    "starter/sealed",
    "starter/reference",
    "starter/reference_tests",
    "starter/solution",
    "starter/solutions",
    "starter/answers",
    "public_tests/sealed",
    "public_tests/reference",
    "public_tests/hidden_tests",
    "environment/sealed",
)

EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_d49f1492abb05519b3c18d8a793d37a2",
    "provenance_sha256": "7b06f5c8326e5b149cb21eca38df244194501c4ffb93c9a997e5e2f897a561bc",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}


def canonical_sha256(value):
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ArtifactStructureTests(unittest.TestCase):
    def test_authoritative_required_paths_are_regular_files(self):
        missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
        self.assertEqual(missing, [])

    def test_forbidden_paths_do_not_exist_even_as_dangling_links(self):
        present = [name for name in FORBIDDEN if os.path.lexists(ROOT / name)]
        self.assertEqual(present, [])

    def test_archive_tree_contains_only_regular_files_and_directories(self):
        unusual = [
            str(path.relative_to(ROOT))
            for path in ROOT.rglob("*")
            if not path.is_file() and not path.is_dir()
        ]
        self.assertEqual(unusual, [])

    def test_manifest_is_exact_and_keeps_partial_status(self):
        manifest = json.loads((ROOT / "MANIFEST.yaml").read_text(encoding="utf-8"))
        self.assertEqual(manifest, EXPECTED_MANIFEST)
        self.assertEqual(
            canonical_sha256(manifest),
            "0a134783939d3d2bd9fc51f0ab33ef43cb40e4c86dc52feceb41248b0886b18e",
        )

    def test_provenance_snapshot_is_frozen(self):
        provenance = json.loads((ROOT / "PROVENANCE.json").read_text(encoding="utf-8"))
        self.assertEqual(
            canonical_sha256(provenance),
            "17238e9005ea6ad305702b2fd5f18b9693608e3ccf4bf89881f929bb46002422",
        )
        self.assertFalse(provenance["license_boundary"]["linked_content_copied"])
        self.assertEqual(
            provenance["snapshot_sha256"], EXPECTED_MANIFEST["provenance_sha256"]
        )

    def test_no_credential_shaped_content(self):
        patterns = (
            re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
            re.compile(r"AKIA[0-9A-Z]{16}"),
            re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
            re.compile(
                r"(?i)\b(?:api[_-]?key|password|secret|access[_-]?token)\b\s*[:=]\s*['\"][^'\"]{8,}['\"]"
            ),
        )
        findings = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.suffix in {".pyc", ".pyo"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for pattern in patterns:
                if pattern.search(text):
                    findings.append(str(path.relative_to(ROOT)))
                    break
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
