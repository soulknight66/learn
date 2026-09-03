import math
from pathlib import Path
import tempfile
import unittest

from minictr.errors import ValidationError
from minictr.paths import resolve_guest_path, validate_rootfs
from minictr.spec import ContainerSpec


def mapping(root="/tmp/root"):
    return {
        "id": "box_1",
        "rootfs": root,
        "command": ["/bin/true"],
        "hostname": "box-1",
        "env": {"Z": "last", "A": "first"},
        "timeout_seconds": 1.5,
        "readonly_root": True,
        "network": False,
    }


class SpecTests(unittest.TestCase):
    def test_round_trip_and_copy_isolation(self):
        raw = mapping()
        spec = ContainerSpec.from_mapping(raw)
        self.assertEqual(spec.env_items, (("A", "first"), ("Z", "last")))
        rebuilt = spec.to_mapping()
        rebuilt["command"].append("changed")
        rebuilt["env"]["A"] = "changed"
        self.assertEqual(spec.command, ("/bin/true",))
        self.assertEqual(spec.env["A"], "first")

    def test_defaults_are_fail_closed(self):
        raw = {"id": "box", "rootfs": "/tmp/root", "command": ["/bin/true"]}
        spec = ContainerSpec.from_mapping(raw)
        self.assertTrue(spec.readonly_root)
        self.assertFalse(spec.network)
        self.assertEqual(spec.hostname, "box")

    def test_rejects_bad_ids_commands_and_paths(self):
        changes = [
            ("id", "Upper"),
            ("id", "a" * 33),
            ("rootfs", "relative/root"),
            ("rootfs", "/tmp/bad\0root"),
            ("command", []),
            ("command", ["ok", ""]),
            ("command", ["ok", "bad\0arg"]),
        ]
        for field, bad in changes:
            with self.subTest(field=field, bad=bad):
                raw = mapping()
                raw[field] = bad
                with self.assertRaises(ValidationError):
                    ContainerSpec.from_mapping(raw)

    def test_rejects_timeout_edge_cases_and_bool(self):
        for bad in (False, math.nan, math.inf, -math.inf, 0.09, 300.01, "1"):
            with self.subTest(value=bad):
                raw = mapping()
                raw["timeout_seconds"] = bad
                with self.assertRaises(ValidationError):
                    ContainerSpec.from_mapping(raw)

    def test_rejects_environment_and_boolean_confusion(self):
        candidates = [
            {**mapping(), "env": {"BAD-NAME": "x"}},
            {**mapping(), "env": {"OK": "bad\0value"}},
            {**mapping(), "env": {str(index): "x" for index in range(129)}},
            {**mapping(), "readonly_root": 1},
            {**mapping(), "network": 0},
            {**mapping(), "extra": "rejected"},
        ]
        for raw in candidates:
            with self.subTest(raw=raw):
                with self.assertRaises(ValidationError):
                    ContainerSpec.from_mapping(raw)


class PathTests(unittest.TestCase):
    def test_wrong_root_types_raise_validation_error(self):
        for path in (".", None, 17):
            with self.subTest(path=path), self.assertRaises(ValidationError):
                validate_rootfs(path)

    def test_resolves_inside_and_rejects_relative_or_parent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"
            (root / "etc").mkdir(parents=True)
            self.assertEqual(resolve_guest_path(root, "/etc/new"), root / "etc" / "new")
            for bad in ("etc/new", "/../outside", "/etc/../../outside", "bad\0path"):
                with self.subTest(path=bad), self.assertRaises(ValidationError):
                    resolve_guest_path(root, bad)

    def test_rejects_symlink_escape_and_root_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "root"
            outside = base / "root-sibling"
            root.mkdir()
            outside.mkdir()
            (root / "jump").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValidationError):
                resolve_guest_path(root, "/jump/item")
            alias = base / "alias"
            alias.symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValidationError):
                validate_rootfs(alias)

    def test_rejects_missing_and_regular_file_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            file_path = base / "file"
            file_path.write_text("not a root", encoding="utf-8")
            for path in (base / "missing", file_path, Path("relative"), Path("/")):
                with self.subTest(path=path), self.assertRaises(ValidationError):
                    validate_rootfs(path)


if __name__ == "__main__":
    unittest.main()
