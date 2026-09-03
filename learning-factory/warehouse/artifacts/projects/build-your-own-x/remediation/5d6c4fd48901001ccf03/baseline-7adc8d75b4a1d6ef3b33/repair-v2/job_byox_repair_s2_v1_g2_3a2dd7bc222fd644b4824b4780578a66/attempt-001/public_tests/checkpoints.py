"""Opt-in executable checkpoints for learner-owned stages 3 through 5.

This module is intentionally named outside unittest discovery's ``test*.py`` pattern. Run one
stage class after implementing that stage; the untouched starter should fail these checkpoints.
"""

from contextlib import redirect_stderr
import io
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

import minictr.child as child
from minictr.planner import LaunchPlan, build_launch_plan
from minictr.registry import Registry
from minictr.runner import Runner
from minictr.spec import ContainerSpec


def make_spec(rootfs: str, container_id: str = "checkpoint") -> ContainerSpec:
    return ContainerSpec.from_mapping(
        {"id": container_id, "rootfs": rootfs, "command": ["/bin/true"]}
    )


class Stage3PlannerCheckpoint(unittest.TestCase):
    def test_builds_an_inert_namespace_plan(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "root"
            (root / "proc").mkdir(parents=True)
            unshare = base / "unshare"
            unshare.write_text("test fixture", encoding="utf-8")
            unshare.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

            plan = build_launch_plan(make_spec(str(root)), str(unshare))

        self.assertIsInstance(plan, LaunchPlan)
        self.assertEqual(plan.argv[0], str(unshare))
        self.assertIn("--user", plan.argv)
        self.assertIn("--mount", plan.argv)
        self.assertIn("--pid", plan.argv)
        self.assertNotIn("/bin/true", plan.argv)

    def test_child_bounds_its_input_before_setup(self):
        stream = io.TextIOWrapper(io.BytesIO(b"x" * (1024 * 1024 + 1)), encoding="utf-8")
        errors = io.StringIO()
        with mock.patch.object(child.sys, "stdin", stream), redirect_stderr(errors):
            result = child.main()
        self.assertEqual(result, 125)
        self.assertIn("exceeds 1 MiB", errors.getvalue())


class Stage4RegistryCheckpoint(unittest.TestCase):
    def test_persists_a_happy_path_lifecycle(self):
        with tempfile.TemporaryDirectory() as temporary:
            registry = Registry(Path(temporary) / "state.sqlite3")
            try:
                created = registry.create(
                    make_spec("/tmp/checkpoint-root", "lifecycle"),
                    "2026-01-02T03:04:05Z",
                )
                running = registry.claim_start("lifecycle", 123, "2026-01-02T03:04:06Z")
                exited = registry.finish(
                    "lifecycle", 0, "/tmp/lifecycle.log", "2026-01-02T03:04:07Z"
                )
                durable = registry.get("lifecycle")
            finally:
                registry.close()

        self.assertEqual(created.state, "CREATED")
        self.assertEqual((running.state, running.pid), ("RUNNING", 123))
        self.assertEqual((exited.state, exited.exit_code), ("EXITED", 0))
        self.assertEqual(durable, exited)


class Stage5RunnerCheckpoint(unittest.TestCase):
    def test_uses_the_injected_process_and_returns_captured_output(self):
        observed = {}

        class Process:
            returncode = 0
            pid = 321

            def communicate(self, **kwargs):
                observed["communicate"] = kwargs
                return b"hello", b""

        def factory(argv, **kwargs):
            observed["argv"] = argv
            observed["launch"] = kwargs
            return Process()

        plan = LaunchPlan(("/fixture/unshare", "--user"), (("LANG", "C"),), 0.5)
        result = Runner(popen_factory=factory).run(plan, b'{"z":2,"a":1}')

        self.assertEqual((result.exit_code, result.stdout, result.stderr), (0, b"hello", b""))
        self.assertFalse(result.timed_out)
        self.assertEqual(observed["argv"], list(plan.argv))
        self.assertFalse(observed["launch"]["shell"])
        self.assertTrue(observed["launch"]["start_new_session"])
        self.assertEqual(observed["communicate"]["input"], b'{"a":1,"z":2}')


if __name__ == "__main__":
    unittest.main()
