from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from minibox.errors import RunError
from minibox.models import ContainerSpec, ContainerState
from minibox.runtime import Runner
from minibox.state import StateStore


class DirectBackend:
    def build_argv(self, rootfs: Path, spec: ContainerSpec) -> tuple[str, ...]:
        return spec.argv


class MissingBackend:
    def build_argv(self, rootfs: Path, spec: ContainerSpec) -> tuple[str, ...]:
        return ("/minibox-path-that-does-not-exist",)


class ReferenceRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.rootfs = self.base / "rootfs"
        self.rootfs.mkdir()
        self.store = StateStore(self.base / "state.sqlite3")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def add_spec(self, argv: tuple[str, ...], container_id: str = "one") -> None:
        self.store.create(ContainerSpec(container_id, "base", argv))

    def runner(self, **values: object) -> Runner:
        return Runner(
            self.store,
            lambda container_id: self.rootfs,
            backend=values.pop("backend", DirectBackend()),  # type: ignore[arg-type]
            **values,  # type: ignore[arg-type]
        )

    def test_nonzero_payload_is_exited_and_parent_environment_is_not_inherited(self) -> None:
        code = (
            "import os,sys; "
            "print(os.environ.get('PARENT_ONLY_MARKER', 'missing')); "
            "sys.stderr.write('diagnostic'); sys.exit(3)"
        )
        self.add_spec((sys.executable, "-c", code))
        with mock.patch.dict(os.environ, {"PARENT_ONLY_MARKER": "present"}):
            result = self.runner(timeout=2).run("one")
        self.assertEqual(result.returncode, 3)
        self.assertEqual(result.stdout, b"missing\n")
        self.assertEqual(result.stderr, b"diagnostic")
        record = self.store.get("one")
        self.assertEqual(record.state, ContainerState.EXITED)
        self.assertEqual(record.exit_code, 3)

    def test_output_is_drained_but_retained_bytes_are_bounded(self) -> None:
        code = "import sys; sys.stdout.buffer.write(b'x' * 20000); sys.stderr.buffer.write(b'y' * 20000)"
        self.add_spec((sys.executable, "-c", code))
        result = self.runner(timeout=2, max_output=127).run("one")
        self.assertEqual(len(result.stdout), 127)
        self.assertEqual(len(result.stderr), 127)
        self.assertTrue(result.output_truncated)
        self.assertEqual(self.store.get("one").state, ContainerState.EXITED)

    def test_timeout_kills_group_and_records_failed(self) -> None:
        self.add_spec((sys.executable, "-c", "import time; time.sleep(10)"))
        result = self.runner(timeout=0.05).run("one")
        self.assertTrue(result.timed_out)
        self.assertEqual(self.store.get("one").state, ContainerState.FAILED)
        self.assertIsNone(self.store.get("one").exit_code)

    def test_launch_failure_records_failed_and_raises_domain_error(self) -> None:
        self.add_spec((sys.executable, "-c", "pass"))
        with self.assertRaises(RunError):
            self.runner(backend=MissingBackend(), timeout=1).run("one")
        self.assertEqual(self.store.get("one").state, ContainerState.FAILED)
        self.assertEqual(
            [event.to_state for event in self.store.events("one")],
            [ContainerState.CREATED, ContainerState.RUNNING, ContainerState.FAILED],
        )


if __name__ == "__main__":
    unittest.main()
