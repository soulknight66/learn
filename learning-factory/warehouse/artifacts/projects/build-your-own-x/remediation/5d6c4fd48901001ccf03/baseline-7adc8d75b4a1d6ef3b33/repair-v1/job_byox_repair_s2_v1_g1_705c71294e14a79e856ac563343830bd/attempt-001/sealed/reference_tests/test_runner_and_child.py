import json
from pathlib import Path
import signal
import subprocess
import tempfile
import unittest
from unittest import mock

import minictr.child as child
from minictr.errors import ValidationError
from minictr.planner import LaunchPlan
from minictr.runner import MAX_PAYLOAD, Runner
from minictr.spec import ContainerSpec


def plan():
    return LaunchPlan(("/usr/bin/unshare", "--user", "--", "/python"), (("LANG", "C"),), 1.25)


class SuccessfulProcess:
    pid = 4321
    returncode = 0

    def __init__(self):
        self.calls = []

    def communicate(self, **kwargs):
        self.calls.append(kwargs)
        return b"output", b"warning"


class TimeoutProcess:
    pid = 8765
    returncode = None

    def __init__(self):
        self.calls = 0

    def communicate(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            raise subprocess.TimeoutExpired("unshare", kwargs["timeout"])
        self.returncode = -signal.SIGKILL
        return b"partial", b"timed out"


class RunnerTests(unittest.TestCase):
    def test_launches_argv_without_shell_and_canonicalizes_json(self):
        process = SuccessfulProcess()
        observed = {}

        def factory(argv, **kwargs):
            observed["argv"] = argv
            observed["kwargs"] = kwargs
            return process

        result = Runner(popen_factory=factory, killpg=lambda *_: self.fail("unexpected kill")).run(
            plan(), b'{ "z": 2, "a": 1 }'
        )
        self.assertEqual(result.exit_code, 0)
        self.assertFalse(result.timed_out)
        self.assertEqual(observed["argv"], list(plan().argv))
        self.assertIs(observed["kwargs"]["stdin"], subprocess.PIPE)
        self.assertFalse(observed["kwargs"]["shell"])
        self.assertTrue(observed["kwargs"]["start_new_session"])
        self.assertEqual(process.calls[0]["input"], b'{"a":1,"z":2}')
        self.assertEqual(process.calls[0]["timeout"], 1.25)

    def test_timeout_kills_process_group_and_reaps(self):
        process = TimeoutProcess()
        kills = []
        result = Runner(
            popen_factory=lambda *_args, **_kwargs: process,
            killpg=lambda pid, sig: kills.append((pid, sig)),
        ).run(plan(), b"{}")
        self.assertTrue(result.timed_out)
        self.assertEqual(result.exit_code, -signal.SIGKILL)
        self.assertEqual(kills, [(process.pid, signal.SIGKILL)])
        self.assertEqual(process.calls, 2)

    def test_rejects_non_json_non_bytes_and_oversized_payload(self):
        runner = Runner(popen_factory=lambda *_args, **_kwargs: self.fail("must not launch"))
        for payload in (b"not json", "{}", b"x" * (MAX_PAYLOAD + 1)):
            with self.subTest(kind=type(payload).__name__), self.assertRaises(ValidationError):
                runner.run(plan(), payload)


class ChildSetupTests(unittest.TestCase):
    def _spec(self, root: Path, readonly=True):
        return ContainerSpec.from_mapping(
            {
                "id": "child",
                "rootfs": str(root),
                "command": ["/bin/true"],
                "readonly_root": readonly,
            }
        )

    def test_private_bind_readonly_hostname_then_chroot(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "proc").mkdir()
            spec = self._spec(root)
            events = []
            with (
                mock.patch.object(child, "validate_rootfs", return_value=root),
                mock.patch.object(child, "_mount", side_effect=lambda *args: events.append(("mount", args))),
                mock.patch.object(child, "_set_hostname", side_effect=lambda name: events.append(("hostname", name))),
                mock.patch.object(child.os, "chroot", side_effect=lambda path: events.append(("chroot", path))),
                mock.patch.object(child.os, "chdir", side_effect=lambda path: events.append(("chdir", path))),
            ):
                child._prepare_root(spec)
            self.assertEqual(
                events,
                [
                    ("mount", (None, "/", child.MS_REC | child.MS_PRIVATE)),
                    ("mount", (str(root), str(root), child.MS_BIND | child.MS_REC)),
                    ("mount", (None, str(root), child.MS_BIND | child.MS_REMOUNT | child.MS_RDONLY)),
                    ("mount", ("proc", str(root / "proc"), child.MS_NOSUID | child.MS_NODEV | child.MS_NOEXEC, "proc")),
                    ("hostname", "child"),
                    ("chroot", root),
                    ("chdir", "/"),
                ],
            )

    def test_writable_root_omits_readonly_remount(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "proc").mkdir()
            spec = self._spec(root, readonly=False)
            with (
                mock.patch.object(child, "validate_rootfs", return_value=root),
                mock.patch.object(child, "_mount") as mount,
                mock.patch.object(child, "_set_hostname"),
                mock.patch.object(child.os, "chroot"),
                mock.patch.object(child.os, "chdir"),
            ):
                child._prepare_root(spec)
            self.assertEqual(mount.call_count, 3)


if __name__ == "__main__":
    unittest.main()
