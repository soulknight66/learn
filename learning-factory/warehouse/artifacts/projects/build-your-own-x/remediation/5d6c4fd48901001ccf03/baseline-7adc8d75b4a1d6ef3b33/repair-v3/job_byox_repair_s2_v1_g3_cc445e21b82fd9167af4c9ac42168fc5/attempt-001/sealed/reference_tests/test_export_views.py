import json
from pathlib import Path
import tempfile
import unittest

from environment import export_views


class ExportViewsTests(unittest.TestCase):
    def test_exports_separated_complete_views_with_hash_manifests(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "export"
            summaries = export_views.create_views(destination)
            learner = destination / "learner"
            instructor = destination / "instructor"

            self.assertEqual({item["role"] for item in summaries}, {"learner", "instructor"})
            self.assertEqual(
                {path.name for path in learner.iterdir()},
                set(export_views.LEARNER_TOP_LEVEL),
            )
            for omitted in ("sealed", "adversarial", "debugging", "review_exercises", "benchmarks"):
                self.assertFalse((learner / omitted).exists())
            self.assertTrue((learner / "starter/minictr/spec.py").is_file())
            self.assertTrue((instructor / "sealed/reference/minictr/spec.py").is_file())
            self.assertTrue((instructor / "sealed/reference_tests/test_export_views.py").is_file())

            manifest = json.loads(
                (learner / export_views.MANIFEST_PATH).read_text(encoding="utf-8")
            )
            listed = {item["path"] for item in manifest["files"]}
            actual = {
                path.relative_to(learner).as_posix()
                for path in learner.rglob("*")
                if path.is_file() and path.relative_to(learner) != export_views.MANIFEST_PATH
            }
            self.assertEqual(listed, actual)
            self.assertEqual(export_views.verify_view(learner, "learner")["role"], "learner")
            self.assertEqual(
                export_views.verify_view(instructor, "instructor")["role"], "instructor"
            )

    def test_verifier_rejects_tampering_and_extra_entries(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "export"
            export_views.create_views(destination)
            learner = destination / "learner"
            readme = learner / "starter/README.md"
            readme.write_text(readme.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")
            with self.assertRaises(export_views.ExportError):
                export_views.verify_view(learner, "learner")

            instructor = destination / "instructor"
            (instructor / "unexpected").write_text("extra", encoding="utf-8")
            with self.assertRaises(export_views.ExportError):
                export_views.verify_view(instructor, "instructor")


if __name__ == "__main__":
    unittest.main()
