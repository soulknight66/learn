from pathlib import Path
import shutil
import tempfile
import unittest

from sealed.reference_tests import verify_pack


ROOT = Path(__file__).resolve().parents[2]
TEMP_ROOT = ROOT / "sealed" / "reference_tests" / "build"


class PackVerifierBoundaryTests(unittest.TestCase):
    def copy_pack(self, destination: Path) -> None:
        ignore = shutil.ignore_patterns("build", "__pycache__", "*.o", "*.pyc")
        for name in sorted(verify_pack.ALLOWED_TOP_LEVEL):
            source = ROOT / name
            target = destination / name
            if source.is_dir():
                shutil.copytree(source, target, ignore=ignore)
            else:
                shutil.copy2(source, target)

    def assert_rejected(self, name: str, make_entry) -> None:
        TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="verify-pack-", dir=TEMP_ROOT
        ) as directory:
            candidate = Path(directory) / "candidate"
            candidate.mkdir()
            self.copy_pack(candidate)
            make_entry(candidate / name)
            with self.assertRaisesRegex(
                verify_pack.VerificationError,
                rf"unexpected top-level entries: {name}",
            ):
                verify_pack.verify(candidate)

    def test_allowlisted_pack_is_accepted(self) -> None:
        TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="verify-pack-", dir=TEMP_ROOT
        ) as directory:
            candidate = Path(directory) / "candidate"
            candidate.mkdir()
            self.copy_pack(candidate)
            self.assertEqual(
                verify_pack.verify(candidate)[-1],
                "whole-archive credential-pattern scan: PASS",
            )

    def test_unexpected_top_level_file_is_rejected(self) -> None:
        self.assert_rejected(
            "UNEXPECTED.txt",
            lambda path: path.write_text("unexpected entry\n", encoding="ascii"),
        )

    def test_unexpected_top_level_symlink_is_rejected(self) -> None:
        self.assert_rejected(
            "UNEXPECTED_LINK",
            lambda path: path.symlink_to("README.md"),
        )


if __name__ == "__main__":
    unittest.main()
