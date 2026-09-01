from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from minibox.cli import main
from minibox.errors import ContainerExists
from minibox.models import ContainerSpec
from minibox.workspace import Workspace


def make_layer(path: Path) -> None:
    with tarfile.open(path, "w") as archive:
        data = b"rootfs-data"
        info = tarfile.TarInfo("opt/data")
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))


class ReferenceWorkspaceTests(unittest.TestCase):
    def test_manifest_records_digest_provenance_and_validation_labels(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            layer = base / "layer.tar"
            make_layer(layer)
            workspace = Workspace(base / "store")
            stats = workspace.import_image("base", layer)
            manifest = json.loads(
                (workspace.images / "base" / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["image_id"], "base")
            self.assertEqual(len(manifest["layer_sha256"]), 64)
            self.assertEqual(manifest["provenance"], {"kind": "local-layer-tar"})
            self.assertEqual(manifest["validation_labels"], ["ARCHIVE_VALIDATED", "NOT_EXECUTED"])
            self.assertEqual(manifest["stats"]["bytes_written"], stats.bytes_written)

    def test_duplicate_container_does_not_replace_rootfs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            layer = base / "layer.tar"
            make_layer(layer)
            workspace = Workspace(base / "store")
            workspace.import_image("base", layer)
            spec = ContainerSpec("one", "base", ("/bin/true",))
            workspace.create(spec)
            rootfs = workspace.rootfs_for("one")
            (rootfs / "marker").write_bytes(b"owned")
            with self.assertRaises(ContainerExists):
                workspace.create(spec)
            self.assertEqual((rootfs / "marker").read_bytes(), b"owned")

    def test_cli_import_create_inspect_and_errors_are_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            layer = base / "layer.tar"
            make_layer(layer)
            store = base / "store"
            output = io.StringIO()
            with redirect_stdout(output):
                status = main(["--store", str(store), "image-import", "base", str(layer)])
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(output.getvalue())["image_id"], "base")

            output = io.StringIO()
            with redirect_stdout(output):
                status = main(
                    [
                        "--store",
                        str(store),
                        "create",
                        "one",
                        "--image",
                        "base",
                        "--env",
                        "MODE=test",
                        "--",
                        "/bin/true",
                    ]
                )
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(output.getvalue())["state"], "CREATED")

            output = io.StringIO()
            with redirect_stdout(output):
                status = main(["--store", str(store), "inspect", "one"])
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(output.getvalue())["spec"]["env"], {"MODE": "test"})

            errors = io.StringIO()
            with redirect_stderr(errors):
                status = main(["--store", str(store), "inspect", "missing"])
            self.assertEqual(status, 2)
            self.assertEqual(json.loads(errors.getvalue())["error"], "ContainerNotFound")


if __name__ == "__main__":
    unittest.main()
