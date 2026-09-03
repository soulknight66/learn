from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

import minictr.cli as cli
import minictr.preflight as preflight
from minictr.runner import RunResult


class PreflightHelperTests(unittest.TestCase):
    @staticmethod
    def _payload(root: Path) -> bytes:
        return json.dumps(
            {"id": "probe", "rootfs": str(root), "command": ["/bin/true"]}
        ).encode()

    def test_success_performs_setup_without_execing_workload(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "proc").mkdir()
            stream = io.TextIOWrapper(io.BytesIO(self._payload(root)), encoding="utf-8")
            with mock.patch.object(preflight.sys, "stdin", stream), mock.patch.object(
                preflight, "_prepare_root"
            ) as prepare:
                result = preflight.main()
        self.assertEqual(result, 0)
        prepare.assert_called_once()

    def test_unsupported_readonly_setup_is_actionable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "proc").mkdir()
            stream = io.TextIOWrapper(io.BytesIO(self._payload(root)), encoding="utf-8")
            errors = io.StringIO()
            with (
                mock.patch.object(preflight.sys, "stdin", stream),
                mock.patch.object(preflight, "_prepare_root", side_effect=PermissionError(1, "denied")),
                redirect_stderr(errors),
            ):
                result = preflight.main()
        self.assertEqual(result, preflight.EX_UNAVAILABLE)
        self.assertIn("UNSUPPORTED read-only root setup", errors.getvalue())
        self.assertIn("workload was not started", errors.getvalue())

    def test_rejects_oversized_payload_before_setup(self):
        stream = io.TextIOWrapper(io.BytesIO(b"x" * (1024 * 1024 + 1)), encoding="utf-8")
        with mock.patch.object(preflight.sys, "stdin", stream), mock.patch.object(
            preflight, "_prepare_root"
        ) as prepare:
            result = preflight.main()
        self.assertEqual(result, preflight.EX_DATAERR)
        prepare.assert_not_called()


class CliPreflightTests(unittest.TestCase):
    def test_failed_preflight_does_not_start_workload(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "root"
            (root / "proc").mkdir(parents=True)
            spec_path = base / "spec.json"
            spec_path.write_text(
                json.dumps({"id": "probe", "rootfs": str(root), "command": ["/bin/true"]}),
                encoding="utf-8",
            )
            unshare = base / "unshare"
            unshare.write_text("fixture", encoding="utf-8")
            unshare.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

            class FakeRunner:
                def __init__(self):
                    self.calls = 0

                def run(self, _plan, _payload):
                    self.calls += 1
                    return RunResult(preflight.EX_UNAVAILABLE, b"", b"", False)

            runner = FakeRunner()
            errors = io.StringIO()
            with mock.patch.object(cli, "Runner", return_value=runner), redirect_stderr(errors):
                result = cli.main(
                    ["run", str(spec_path), "--unshare", str(unshare), "--allow-execution"]
                )
        self.assertEqual(result, preflight.EX_UNAVAILABLE)
        self.assertEqual(runner.calls, 1)
        self.assertIn("workload was not started", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
