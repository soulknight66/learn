import json
import tempfile
import unittest
from dataclasses import is_dataclass
from pathlib import Path

from minibox.config import ContainerSpec, from_dict, load_spec
from minibox.errors import SpecError


class ContainerSpecPublicTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.rootfs = Path(self.temporary_directory.name) / "rootfs"
        self.rootfs.mkdir()

    def minimal_data(self):
        return {
            "schema_version": 1,
            "rootfs": str(self.rootfs),
            "argv": ["/bin/hello"],
        }

    def test_minimal_spec_uses_documented_defaults(self):
        spec = from_dict(self.minimal_data())

        self.assertTrue(is_dataclass(spec))
        self.assertIsInstance(spec, ContainerSpec)
        self.assertEqual(spec.schema_version, 1)
        self.assertEqual(Path(spec.rootfs), self.rootfs)
        self.assertEqual(tuple(spec.argv), ("/bin/hello",))
        self.assertEqual(dict(spec.env), {})
        self.assertEqual(spec.hostname, "minibox")
        self.assertEqual(spec.network_mode, "none")
        self.assertEqual(spec.timeout_seconds, 30.0)

    def test_all_supported_fields_are_accepted(self):
        data = self.minimal_data()
        data.update(
            {
                "argv": ["tool", "--message", "hello world"],
                "env": {"PATH": "/tools:/bin", "EMPTY": ""},
                "hostname": "worker-7",
                "network_mode": "host",
                "timeout_seconds": 2.5,
            }
        )

        spec = from_dict(data)

        self.assertEqual(tuple(spec.argv), ("tool", "--message", "hello world"))
        self.assertEqual(dict(spec.env), {"PATH": "/tools:/bin", "EMPTY": ""})
        self.assertEqual(spec.hostname, "worker-7")
        self.assertEqual(spec.network_mode, "host")
        self.assertEqual(spec.timeout_seconds, 2.5)

    def test_unknown_keys_and_wrong_schema_versions_are_rejected(self):
        unknown = self.minimal_data()
        unknown["privileged"] = True
        with self.assertRaises(SpecError):
            from_dict(unknown)

        wrong_version = self.minimal_data()
        wrong_version["schema_version"] = 2
        with self.assertRaises(SpecError):
            from_dict(wrong_version)

    def test_rootfs_must_be_an_absolute_existing_directory(self):
        relative = self.minimal_data()
        relative["rootfs"] = "relative/rootfs"
        with self.assertRaises(SpecError):
            from_dict(relative)

        missing = self.minimal_data()
        missing["rootfs"] = str(self.rootfs / "missing")
        with self.assertRaises(SpecError):
            from_dict(missing)

        regular_file = self.rootfs / "not-a-directory"
        regular_file.write_text("data", encoding="utf-8")
        not_a_directory = self.minimal_data()
        not_a_directory["rootfs"] = str(regular_file)
        with self.assertRaises(SpecError):
            from_dict(not_a_directory)

    def test_argv_must_contain_at_least_one_nonempty_string(self):
        for bad_argv in ([], [""], ["ok", ""], ["ok", 3], "echo"):
            with self.subTest(argv=bad_argv):
                data = self.minimal_data()
                data["argv"] = bad_argv
                with self.assertRaises(SpecError):
                    from_dict(data)

    def test_load_spec_reads_a_json_object(self):
        path = Path(self.temporary_directory.name) / "spec.json"
        path.write_text(json.dumps(self.minimal_data()), encoding="utf-8")

        spec = load_spec(path)

        self.assertEqual(Path(spec.rootfs), self.rootfs)
        self.assertEqual(tuple(spec.argv), ("/bin/hello",))

    def test_load_spec_wraps_invalid_json_as_a_spec_error(self):
        path = Path(self.temporary_directory.name) / "broken.json"
        path.write_text("{not json", encoding="utf-8")

        with self.assertRaises(SpecError):
            load_spec(path)


if __name__ == "__main__":
    unittest.main()
