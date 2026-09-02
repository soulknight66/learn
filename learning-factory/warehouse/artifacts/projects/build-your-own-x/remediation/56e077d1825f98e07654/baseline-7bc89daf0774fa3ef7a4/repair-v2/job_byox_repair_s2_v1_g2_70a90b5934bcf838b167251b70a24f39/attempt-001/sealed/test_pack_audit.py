import json
import tempfile
import unittest
from pathlib import Path

import pack_audit


class PackAuditTests(unittest.TestCase):
    def test_json_parse_failures_are_isolated_by_document(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            current = root / "MANIFEST.yaml"
            current.write_text('{"status": "GENERATED"}\n', encoding="utf-8")
            failures = []

            parsed_current = pack_audit._load_json(current, "manifest", failures)
            parsed_prior = pack_audit._load_json(
                root / "missing-prior.json", "prior provenance", failures
            )

            self.assertEqual(parsed_current, {"status": "GENERATED"})
            self.assertIsNone(parsed_prior)
            self.assertEqual(len(failures), 1)
            self.assertIn("prior provenance parse failure", failures[0])

    def test_content_digest_is_creation_order_independent_and_content_bound(self):
        with tempfile.TemporaryDirectory() as first_temp, tempfile.TemporaryDirectory() as second_temp:
            first = Path(first_temp)
            second = Path(second_temp)
            (first / "dir").mkdir()
            (first / "dir" / "b").write_bytes(b"beta")
            (first / "a").write_bytes(b"alpha")
            (second / "a").write_bytes(b"alpha")
            (second / "dir").mkdir()
            (second / "dir" / "b").write_bytes(b"beta")

            self.assertEqual(
                pack_audit.content_digest(first), pack_audit.content_digest(second)
            )
            (second / "dir" / "b").write_bytes(b"changed")
            self.assertNotEqual(
                pack_audit.content_digest(first), pack_audit.content_digest(second)
            )

    def test_prior_record_shape_is_explicit(self):
        record = json.loads(
            (Path(__file__).with_name("prior_baseline.json")).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(set(record), pack_audit.PRIOR_RECORD_KEYS)
        self.assertEqual(
            record["content_digest_algorithm"], pack_audit.CONTENT_DIGEST_ALGORITHM
        )
        for field, expected in pack_audit.EXPECTED_PRIOR_ARTIFACT.items():
            self.assertEqual(record[field], expected)

    def test_current_pack_audit_is_self_contained(self):
        pack_root = Path(__file__).resolve().parents[1]
        observations = pack_audit.audit(pack_root)
        self.assertIn("manifest_exactness=PASS", observations)
        self.assertIn("provenance_consistency=PASS", observations)
        self.assertIn("historical_comparison=SKIPPED(no prior input)", observations)


if __name__ == "__main__":
    unittest.main()
