from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pydocklet import ContainerState, Docklet, InvalidProcess, ProcessRunner

from sealed.reference_tests.helpers import write_regular_layer


class PrivateRunnerTests(unittest.TestCase):
    def test_parent_environment_is_not_inherited(self) -> None:
        previous = os.environ.get("AMBIENT_MARKER")
        os.environ["AMBIENT_MARKER"] = "parent-value"
        try:
            with tempfile.TemporaryDirectory() as temporary:
                result = ProcessRunner().run(
                    [
                        sys.executable,
                        "-c",
                        "import os; print(os.environ.get('AMBIENT_MARKER', 'absent'))",
                    ],
                    Path(temporary),
                )
        finally:
            if previous is None:
                os.environ.pop("AMBIENT_MARKER", None)
            else:
                os.environ["AMBIENT_MARKER"] = previous
        self.assertEqual(result.stdout, "absent\n")

    def test_invalid_environment_and_timeout_values_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cwd = Path(temporary)
            for environment in ({"BAD-NAME": "x"}, {"OK": "bad\0value"}):
                with self.subTest(environment=environment):
                    with self.assertRaises(InvalidProcess):
                        ProcessRunner().run([sys.executable, "-c", "pass"], cwd, environment)
            for timeout in (0, -1, float("inf"), float("nan"), True):
                with self.subTest(timeout=timeout):
                    with self.assertRaises(InvalidProcess):
                        ProcessRunner().run([sys.executable, "-c", "pass"], cwd, timeout=timeout)

    def test_invalid_utf8_is_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = ProcessRunner().run(
                [sys.executable, "-c", "import os; os.write(1, bytes([255]))"], Path(temporary)
            )
        self.assertEqual(result.stdout, "\ufffd")

    def test_serialized_truncation_marker_stays_inside_byte_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cwd = Path(temporary)
            short = ProcessRunner(max_output_bytes=5).run(
                [sys.executable, "-c", "print('abcdefgh')"], cwd
            )
            marked = ProcessRunner(max_output_bytes=20).run(
                [sys.executable, "-c", "print('x' * 100)"], cwd
            )
        self.assertEqual(short.stdout, "[...]")
        self.assertLessEqual(len(short.stdout.encode("utf-8")), 5)
        self.assertTrue(marked.stdout.endswith("\n...[truncated]\n"))
        self.assertLessEqual(len(marked.stdout.encode("utf-8")), 20)

    def test_log_scratch_directory_is_injectable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            cwd = work / "cwd"
            scratch = work / "scratch"
            cwd.mkdir()
            scratch.mkdir()
            result = ProcessRunner(scratch_dir=scratch).run(
                [sys.executable, "-c", "print('ok')"], cwd
            )
        self.assertEqual(result.stdout, "ok\n")


class PrivateEngineTests(unittest.TestCase):
    def test_launch_failure_is_durably_finished(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            layer = write_regular_layer(work / "empty.tar", [("data", b"x", 0o644)])
            engine = Docklet(work / "runtime")
            engine.import_image("demo", [layer])
            created = engine.create("demo", ["/definitely/missing/executable"])
            exited = engine.start(created.container_id)
            self.assertEqual(exited.state, ContainerState.EXITED)
            self.assertEqual(exited.exit_code, 125)
            self.assertIn("launch failed", exited.stderr)

    def test_child_receives_root_variable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            script = b"import os\nprint(os.environ['PYDOCKLET_ROOT'])\n"
            layer = write_regular_layer(work / "app.tar", [("app.py", script, 0o644)])
            engine = Docklet(work / "runtime")
            engine.import_image("demo", [layer])
            created = engine.create("demo", [sys.executable, "app.py"], {"PYDOCKLET_ROOT": "wrong"})
            exited = engine.start(created.container_id)
            self.assertEqual(exited.stdout.strip(), str(created.rootfs))


class PrivateCliTests(unittest.TestCase):
    def test_full_cli_flow_emits_parseable_canonical_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            layer = write_regular_layer(
                work / "layer.tar",
                [
                    ("value", b"x", 0o644),
                    ("app.py", b"import os\nprint(os.environ['AUDIENCE'])\n", 0o644),
                ],
            )
            reference_root = Path(__file__).resolve().parents[1] / "reference"
            environment = {
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "PATH": os.defpath,
                "PYTHONPATH": str(reference_root),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            imported = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pydocklet",
                    "--root",
                    str(work / "runtime"),
                    "import",
                    "demo",
                    str(layer),
                ],
                cwd=work,
                env=environment,
                text=True,
                capture_output=True,
                timeout=5,
                check=False,
            )
            self.assertEqual(imported.returncode, 0, imported.stderr)
            payload = json.loads(imported.stdout)
            self.assertEqual(payload["name"], "demo")
            self.assertEqual(imported.stdout, json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")

            created = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pydocklet",
                    "--root",
                    str(work / "runtime"),
                    "create",
                    "demo",
                    "--env",
                    "AUDIENCE=cli",
                    sys.executable,
                    "app.py",
                ],
                cwd=work,
                env=environment,
                text=True,
                capture_output=True,
                timeout=5,
                check=False,
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            created_payload = json.loads(created.stdout)
            self.assertEqual(created_payload["container_id"], "c000001")
            self.assertEqual(created_payload["state"], "CREATED")

            started = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pydocklet",
                    "--root",
                    str(work / "runtime"),
                    "start",
                    "c000001",
                ],
                cwd=work,
                env=environment,
                text=True,
                capture_output=True,
                timeout=5,
                check=False,
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            started_payload = json.loads(started.stdout)
            self.assertEqual(started_payload["state"], "EXITED")
            self.assertEqual(started_payload["stdout"], "cli\n")

            inspected = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pydocklet",
                    "--root",
                    str(work / "runtime"),
                    "inspect",
                    "c000001",
                ],
                cwd=work,
                env=environment,
                text=True,
                capture_output=True,
                timeout=5,
                check=False,
            )
            self.assertEqual(inspected.returncode, 0, inspected.stderr)
            self.assertEqual(json.loads(inspected.stdout), started_payload)

            listed = subprocess.run(
                [sys.executable, "-m", "pydocklet", "--root", str(work / "runtime"), "list"],
                cwd=work,
                env=environment,
                text=True,
                capture_output=True,
                timeout=5,
                check=False,
            )
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertEqual(json.loads(listed.stdout), [started_payload])


if __name__ == "__main__":
    unittest.main()
