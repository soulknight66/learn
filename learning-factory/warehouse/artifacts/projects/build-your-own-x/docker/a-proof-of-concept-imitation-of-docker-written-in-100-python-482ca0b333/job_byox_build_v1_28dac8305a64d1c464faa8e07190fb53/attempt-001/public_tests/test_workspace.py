from __future__ import annotations

import io
from pathlib import Path
import tarfile
import tempfile
import unittest

from minibox.errors import ImageExists
from minibox.models import ContainerSpec, ContainerState
from minibox.workspace import Workspace


class WorkspaceTests(unittest.TestCase):
    def test_image_import_and_container_copy_are_independent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            layer = base / "layer.tar"
            with tarfile.open(layer, "w") as archive:
                payload = b"hello"
                info = tarfile.TarInfo("data/message")
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))

            workspace = Workspace(base / "store")
            workspace.import_image("base", layer)
            with self.assertRaises(ImageExists):
                workspace.import_image("base", layer)
            record = workspace.create(ContainerSpec("one", "base", ("/bin/true",)))
            rootfs = workspace.rootfs_for("one")

            self.assertEqual(record.state, ContainerState.CREATED)
            self.assertEqual((rootfs / "data" / "message").read_bytes(), b"hello")
            (rootfs / "data" / "message").write_bytes(b"changed")
            self.assertEqual((workspace.images / "base" / "rootfs" / "data" / "message").read_bytes(), b"hello")


if __name__ == "__main__":
    unittest.main()
