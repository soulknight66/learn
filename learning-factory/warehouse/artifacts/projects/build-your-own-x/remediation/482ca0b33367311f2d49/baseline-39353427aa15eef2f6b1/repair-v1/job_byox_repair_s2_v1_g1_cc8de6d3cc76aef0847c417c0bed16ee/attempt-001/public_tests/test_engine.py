from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from pydocklet import ContainerState, Docklet, InvalidTransition

from public_tests.helpers import write_layer


class EngineTests(unittest.TestCase):
    def test_import_create_start_and_inspect(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            layer = write_layer(
                work / "app.tar",
                [
                    ("app.py", b"import os\nprint('hello ' + os.environ['AUDIENCE'])\n", 0o644),
                    ("data.txt", b"image-data\n", 0o644),
                ],
            )
            engine = Docklet(work / "runtime")
            image = engine.import_image("demo", [layer])
            self.assertRegex(image.digest, r"^sha256:[0-9a-f]{64}$")

            created = engine.create("demo", [sys.executable, "app.py"], {"AUDIENCE": "learner"})
            self.assertEqual(created.container_id, "c000001")
            self.assertEqual(created.state, ContainerState.CREATED)
            self.assertEqual((created.rootfs / "data.txt").read_text(encoding="utf-8"), "image-data\n")

            exited = engine.start(created.container_id, timeout=2.0)
            self.assertEqual(exited.state, ContainerState.EXITED)
            self.assertEqual(exited.exit_code, 0)
            self.assertEqual(exited.stdout, "hello learner\n")
            self.assertEqual(engine.inspect(created.container_id), exited)

            with self.assertRaises(InvalidTransition):
                engine.start(created.container_id)

    def test_each_container_gets_a_private_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            layer = write_layer(work / "data.tar", [("value", b"original", 0o644)])
            engine = Docklet(work / "runtime")
            engine.import_image("data", [layer])
            first = engine.create("data", [sys.executable, "-c", "pass"])
            second = engine.create("data", [sys.executable, "-c", "pass"])
            (first.rootfs / "value").write_bytes(b"changed")
            self.assertEqual((second.rootfs / "value").read_bytes(), b"original")
            self.assertEqual(first.container_id, "c000001")
            self.assertEqual(second.container_id, "c000002")


if __name__ == "__main__":
    unittest.main()
