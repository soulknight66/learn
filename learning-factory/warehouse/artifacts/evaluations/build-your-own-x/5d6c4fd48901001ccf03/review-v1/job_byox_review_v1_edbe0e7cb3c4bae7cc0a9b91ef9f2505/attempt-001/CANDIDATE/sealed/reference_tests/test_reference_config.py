import json
import math
import os
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType

from minibox.config import from_dict, load_spec
from minibox.errors import BackendUnavailable, RootfsError, SpecError, StateError


class ConfigReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.rootfs = Path(self.temporary_directory.name) / "rootfs"
        self.rootfs.mkdir()

    def valid_data(self):
        return {
            "schema_version": 1,
            "rootfs": str(self.rootfs),
            "argv": ["/bin/program"],
        }

    def assert_bad_field(self, field, values):
        for value in values:
            with self.subTest(field=field, value=value):
                data = self.valid_data()
                data[field] = value
                with self.assertRaises(SpecError):
                    from_dict(data)

    def test_public_exception_types_are_distinct_exceptions(self):
        error_types = (SpecError, RootfsError, StateError, BackendUnavailable)
        for error_type in error_types:
            self.assertTrue(issubclass(error_type, Exception))
        self.assertEqual(len(set(error_types)), len(error_types))

    def test_input_must_be_a_mapping_with_all_required_keys(self):
        for value in (None, [], "spec", 1):
            with self.subTest(value=value):
                with self.assertRaises(SpecError):
                    from_dict(value)

        for key in ("schema_version", "rootfs", "argv"):
            with self.subTest(missing=key):
                data = self.valid_data()
                del data[key]
                with self.assertRaises(SpecError):
                    from_dict(data)

        proxy = MappingProxyType(self.valid_data())
        self.assertEqual(from_dict(proxy).argv, ("/bin/program",))

    def test_no_keys_beyond_the_seven_schema_keys_are_accepted(self):
        for unknown in ("cwd", "mounts", "user", "network", "schemaVersion"):
            with self.subTest(unknown=unknown):
                data = self.valid_data()
                data[unknown] = None
                with self.assertRaises(SpecError):
                    from_dict(data)

    def test_schema_version_is_strictly_integer_one(self):
        self.assert_bad_field("schema_version", [0, 2, -1, "1", 1.0, True, None])

    def test_rootfs_type_and_existence_errors_are_spec_errors(self):
        self.assert_bad_field("rootfs", [None, True, 12, [], {}])

        missing = self.rootfs / "missing"
        self.assert_bad_field("rootfs", [str(missing)])

        regular_file = Path(self.temporary_directory.name) / "regular-file"
        regular_file.write_bytes(b"not a directory")
        self.assert_bad_field("rootfs", [str(regular_file)])

    def test_rootfs_rejects_a_symbolic_link_component(self):
        real_parent = Path(self.temporary_directory.name) / "real-parent"
        real_rootfs = real_parent / "rootfs"
        real_rootfs.mkdir(parents=True)
        linked_parent = Path(self.temporary_directory.name) / "linked-parent"
        try:
            os.symlink(real_parent.name, linked_parent)
        except (NotImplementedError, OSError) as exc:
            self.skipTest("symlinks are unavailable: {}".format(exc))

        data = self.valid_data()
        data["rootfs"] = str(linked_parent / "rootfs")
        with self.assertRaises(SpecError):
            from_dict(data)

    def test_argv_rejects_wrong_container_and_element_types(self):
        self.assert_bad_field(
            "argv",
            [None, "program", {}, [], [""], [1], [True], ["ok", ""]],
        )

    def test_environment_accepts_posix_names_and_string_values(self):
        data = self.valid_data()
        data["env"] = {
            "_": "underscore",
            "_9": "leading underscore",
            "A": "",
            "PATH": "/bin:/usr/bin",
            "mixed_Case09": "value",
        }

        spec = from_dict(data)

        self.assertEqual(dict(spec.env), data["env"])

    def test_environment_rejects_non_posix_names_and_non_string_values(self):
        for name in ("", "9NAME", "HAS-DASH", "HAS.DOT", "A=B", "é", "A N"):
            with self.subTest(name=name):
                data = self.valid_data()
                data["env"] = {name: "value"}
                with self.assertRaises(SpecError):
                    from_dict(data)

        for env in (None, [], "A=value", {1: "value"}, {"A": 1}, {"A": True}):
            with self.subTest(env=env):
                data = self.valid_data()
                data["env"] = env
                with self.assertRaises(SpecError):
                    from_dict(data)

    def test_hostname_uses_a_lowercase_single_label_grammar(self):
        for hostname in ("a", "node-7", "a" * 63, "a" + "-" * 61 + "z"):
            with self.subTest(accepted=hostname):
                data = self.valid_data()
                data["hostname"] = hostname
                self.assertEqual(from_dict(data).hostname, hostname)

        for hostname in (
            "",
            "A",
            "Node-7",
            "-node",
            "node-",
            "node_name",
            "node.example",
            "node name",
            "é",
            "a" * 64,
            None,
            7,
        ):
            with self.subTest(rejected=hostname):
                data = self.valid_data()
                data["hostname"] = hostname
                with self.assertRaises(SpecError):
                    from_dict(data)

    def test_network_mode_is_exactly_none_or_host(self):
        for mode in ("none", "host"):
            with self.subTest(accepted=mode):
                data = self.valid_data()
                data["network_mode"] = mode
                self.assertEqual(from_dict(data).network_mode, mode)

        self.assert_bad_field(
            "network_mode",
            ["bridge", "HOST", " none", "", None, False, 0, [], {}],
        )

    def test_timeout_accepts_finite_numeric_values_in_closed_upper_bound(self):
        for timeout in (0.0001, 1, 1.5, 300):
            with self.subTest(accepted=timeout):
                data = self.valid_data()
                data["timeout_seconds"] = timeout
                self.assertEqual(from_dict(data).timeout_seconds, float(timeout))

        self.assert_bad_field(
            "timeout_seconds",
            [
                0,
                -0.0001,
                300.0001,
                True,
                False,
                "1",
                None,
                math.nan,
                math.inf,
                -math.inf,
            ],
        )

    def test_each_default_is_applied_when_optional_keys_are_absent(self):
        first = from_dict(self.valid_data())
        second = from_dict(self.valid_data())

        self.assertEqual(dict(first.env), {})
        self.assertEqual(first.hostname, "minibox")
        self.assertEqual(first.network_mode, "none")
        self.assertEqual(first.timeout_seconds, 30.0)
        self.assertIsNot(first.env, second.env)

    def test_load_spec_rejects_non_object_json_and_io_errors(self):
        base = Path(self.temporary_directory.name)
        array_path = base / "array.json"
        array_path.write_text(json.dumps([self.valid_data()]), encoding="utf-8")
        with self.assertRaises(SpecError):
            load_spec(array_path)

        with self.assertRaises(SpecError):
            load_spec(base / "does-not-exist.json")

    def test_load_spec_applies_the_same_field_validation(self):
        path = Path(self.temporary_directory.name) / "spec.json"
        data = self.valid_data()
        data["timeout_seconds"] = True
        path.write_text(json.dumps(data), encoding="utf-8")

        with self.assertRaises(SpecError):
            load_spec(path)

    def test_load_spec_rejects_nonstandard_constants_and_duplicate_keys(self):
        base = Path(self.temporary_directory.name)
        rootfs_json = json.dumps(str(self.rootfs))
        nonfinite = base / "nonfinite.json"
        nonfinite.write_text(
            '{"schema_version":1,"rootfs":'
            + rootfs_json
            + ',"argv":["x"],"timeout_seconds":NaN}',
            encoding="utf-8",
        )
        duplicate = base / "duplicate.json"
        duplicate.write_text(
            '{"schema_version":1,"schema_version":1,"rootfs":'
            + rootfs_json
            + ',"argv":["x"]}',
            encoding="utf-8",
        )

        with self.assertRaises(SpecError):
            load_spec(nonfinite)
        with self.assertRaises(SpecError):
            load_spec(duplicate)


if __name__ == "__main__":
    unittest.main()
