import io
import tarfile
import unittest
from pathlib import Path

from sealed.production import artifact_inventory, audit_pack, learner_view


class ProductionPackagingReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack_root = Path(__file__).resolve().parents[2]

    def test_enforced_policy_matches_archived_policy(self):
        self.assertEqual(learner_view.load_policy(), learner_view.expected_policy())

    def test_deterministic_learner_archive_excludes_every_sealed_entry(self):
        first_data, first_report = learner_view.check(self.pack_root)
        second_data, second_report = learner_view.check(self.pack_root)

        self.assertEqual(first_data, second_data)
        self.assertEqual(first_report, second_report)
        self.assertGreater(first_report["sealed_source_entries_scanned"], 0)
        self.assertEqual(first_report["sealed_entries_selected"], 0)

        with tarfile.open(fileobj=io.BytesIO(first_data), mode="r:") as archive:
            names = [member.name.rstrip("/") for member in archive.getmembers()]
        self.assertFalse(
            any(name == "sealed" or name.startswith("sealed/") for name in names)
        )
        self.assertEqual(
            set(name.split("/", 1)[0] for name in names),
            set(learner_view.INCLUDE),
        )

    def test_artifact_inventory_matches_all_pack_files_except_itself(self):
        count, digest = artifact_inventory.verify_inventory(self.pack_root)

        self.assertGreater(count, 0)
        self.assertEqual(len(digest), 64)

    def test_pack_audit_enforces_metadata_structure_and_credential_scan(self):
        report = audit_pack.audit(self.pack_root)

        self.assertEqual(report["status"], "GENERATED")
        self.assertEqual(report["validation_labels"], ["GENERATED", "PARTIAL"])
        self.assertEqual(report["credential_pattern_hits"], [])
        self.assertEqual(report["sealed_entries_selected"], 0)


if __name__ == "__main__":
    unittest.main()
