import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from minibox.cli import main


class CliReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        base = Path(self.temporary_directory.name)
        self.rootfs = base / "rootfs"
        self.rootfs.mkdir()
        self.spec_path = base / "spec.json"
        self.spec_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "rootfs": str(self.rootfs),
                    "argv": ["/bin/tool"],
                }
            ),
            encoding="utf-8",
        )

    def test_check_prints_normalized_nonsecret_summary(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(["check", str(self.spec_path)])

        self.assertEqual(status, 0)
        summary = json.loads(output.getvalue())
        self.assertEqual(summary["schema_version"], 1)
        self.assertEqual(summary["rootfs"], str(self.rootfs))
        self.assertEqual(summary["env_names"], [])
        self.assertNotIn("env", summary)

    def test_plan_prints_the_injected_argv_without_running_it(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(
                [
                    "plan",
                    str(self.spec_path),
                    "--unshare",
                    "/test/unshare",
                    "--python",
                    "/test/python",
                ]
            )

        self.assertEqual(status, 0)
        plan = json.loads(output.getvalue())
        self.assertEqual(plan["argv"][0], "/test/unshare")
        self.assertEqual(plan["argv"][-3:], ["/test/python", "-m", "minibox._child"])
        self.assertEqual(
            plan["namespaces"], ["user", "mount", "pid", "uts", "ipc", "net"]
        )

    def test_invalid_spec_returns_two_and_one_concise_error(self):
        self.spec_path.write_text("not json", encoding="utf-8")
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            status = main(["check", str(self.spec_path)])

        self.assertEqual(status, 2)
        self.assertTrue(error.getvalue().startswith("minibox: "))
        self.assertEqual(len(error.getvalue().splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
