import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from minibox.config import from_dict
from minibox.errors import BackendError, BackendTimeout
from minibox.runtime import LinuxSubprocessBackend


@unittest.skipUnless(sys.platform == "linux", "Linux backend contract")
class LinuxBackendReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.rootfs = Path(self.temporary_directory.name) / "rootfs"
        executable = self.rootfs / "bin" / "payload"
        executable.parent.mkdir(parents=True)
        executable.write_bytes(b"fixture")
        executable.chmod(0o755)
        self.spec = from_dict(
            {
                "schema_version": 1,
                "rootfs": str(self.rootfs),
                "argv": ["/bin/payload", "literal;argument"],
                "env": {"GREETING": "hello"},
                "timeout_seconds": 4,
            }
        )

    @staticmethod
    def fake_process(status, returncode, stdout=b"", stderr=b""):
        captured = {}

        def construct(argv, **kwargs):
            if status:
                os.write(kwargs["pass_fds"][0], status)
            kwargs["stdout"].write(stdout)
            kwargs["stderr"].write(stderr)
            process = mock.Mock()
            process.pid = 424242
            process.returncode = returncode
            def communicate(**communicate_kwargs):
                captured.update(communicate_kwargs)
                return (None, None)

            process.communicate.side_effect = communicate
            process.argv = argv
            captured["argv"] = argv
            captured["popen_kwargs"] = kwargs
            return process

        return construct, captured

    @mock.patch("minibox.runtime.subprocess.Popen")
    def test_ready_protocol_preserves_payload_exit_and_bounds_output(self, popen):
        construct, captured = self.fake_process(
            b"READY\n", 125, stdout=b"abcdef", stderr=b"warning"
        )
        popen.side_effect = construct
        backend = LinuxSubprocessBackend(
            unshare_path=sys.executable,
            python_path=sys.executable,
            max_output_bytes=3,
        )

        result = backend.run(self.spec)

        self.assertEqual(result.exit_code, 125)
        self.assertEqual(result.stdout, b"abc\n[minibox: output truncated]\n")
        self.assertEqual(result.stderr, b"war\n[minibox: output truncated]\n")
        self.assertIsInstance(captured["argv"], list)
        options = captured["popen_kwargs"]
        self.assertNotIn("shell", options)
        self.assertTrue(options["start_new_session"])
        self.assertEqual(options["env"]["LC_ALL"], "C")
        self.assertNotIn("HOME", options["env"])
        sent = json.loads(captured["input"].decode("utf-8"))
        self.assertEqual(sent["argv"], ["/bin/payload", "literal;argument"])
        self.assertEqual(sent["executable"], "/bin/payload")
        self.assertEqual(sent["env"], {"GREETING": "hello"})

    @mock.patch("minibox.runtime.subprocess.Popen")
    def test_helper_error_is_not_confused_with_payload_exit_125(self, popen):
        popen.side_effect = self.fake_process(b"ERROR mount denied\n", 125)[0]
        backend = LinuxSubprocessBackend(
            unshare_path=sys.executable, python_path=sys.executable
        )

        with self.assertRaisesRegex(BackendError, "mount denied"):
            backend.run(self.spec)

    @mock.patch("minibox.runtime.subprocess.Popen")
    def test_launcher_exit_without_readiness_is_backend_failure(self, popen):
        popen.side_effect = self.fake_process(b"", 1)[0]
        backend = LinuxSubprocessBackend(
            unshare_path=sys.executable, python_path=sys.executable
        )

        with self.assertRaisesRegex(BackendError, "before the child reported"):
            backend.run(self.spec)

    @mock.patch("minibox.runtime.os.killpg")
    @mock.patch("minibox.runtime.subprocess.Popen")
    def test_timeout_kills_the_process_group(self, popen, killpg):
        process = mock.Mock()
        process.pid = 31415
        process.returncode = -9
        process.communicate.side_effect = [
            __import__("subprocess").TimeoutExpired(["unshare"], 4),
            (None, None),
        ]
        popen.return_value = process
        backend = LinuxSubprocessBackend(
            unshare_path=sys.executable, python_path=sys.executable
        )

        with self.assertRaises(BackendTimeout):
            backend.run(self.spec)

        killpg.assert_called_once_with(31415, __import__("signal").SIGKILL)


if __name__ == "__main__":
    unittest.main()
