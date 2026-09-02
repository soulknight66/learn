import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
EXPORTER = ROOT / "sealed" / "production" / "learner_view.py"


def load_exporter():
    specification = importlib.util.spec_from_file_location(
        "pebble_learner_view", EXPORTER
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("could not load learner-view exporter")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class LearnerViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.exporter = load_exporter()

    def test_actual_pack_materializes_to_exact_allowlist(self):
        temporary_parent = ROOT / "sealed" / "production"
        with tempfile.TemporaryDirectory(
            prefix=".learner-view-test-", dir=temporary_parent
        ) as directory:
            destination = Path(directory) / "view"
            entries = self.exporter.materialize(ROOT, destination)
            audited = self.exporter.audit_view(destination)

            self.assertEqual(
                {path.name for path in destination.iterdir()},
                set(self.exporter.LEARNER_TOP_LEVEL),
            )
            self.assertFalse((destination / "sealed").exists())
            self.assertFalse((destination / "PROVENANCE.json").exists())
            self.assertEqual(
                audited,
                tuple(str(entry.relative) for entry in entries),
            )
            for entry in entries:
                if not entry.is_directory:
                    self.assertEqual(
                        (destination / entry.relative).read_bytes(),
                        (ROOT / entry.relative).read_bytes(),
                    )

    def test_forbidden_component_in_allowlisted_tree_blocks_export(self):
        temporary_parent = ROOT / "sealed" / "production"
        with tempfile.TemporaryDirectory(
            prefix=".learner-view-policy-test-", dir=temporary_parent
        ) as directory:
            source = Path(directory) / "source"
            source.mkdir()
            for name in self.exporter.LEARNER_TOP_LEVEL:
                path = source / name
                if name in {"starter", "public_tests", "environment"}:
                    path.mkdir()
                else:
                    path.write_text(name + "\n", encoding="utf-8")
            (source / "starter" / "ANSWER.md").write_text(
                "not learner visible\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(
                self.exporter.LearnerViewError, "forbidden component"
            ):
                self.exporter.plan_entries(source)


if __name__ == "__main__":
    unittest.main()
