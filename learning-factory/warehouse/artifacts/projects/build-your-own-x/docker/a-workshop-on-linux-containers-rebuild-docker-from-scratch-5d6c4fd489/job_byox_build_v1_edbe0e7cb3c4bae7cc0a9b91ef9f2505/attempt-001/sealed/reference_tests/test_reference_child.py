import io
import json
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

from minibox import _child


@unittest.skipUnless(sys.platform == "linux", "Linux child protocol")
class ChildProtocolReferenceTests(unittest.TestCase):
    def payload(self, overrides=None):
        data = {
            "schema_version": 1,
            "rootfs": "/rootfs",
            "argv": ["/bin/tool"],
            "env": {},
            "hostname": "minibox",
            "executable": "/bin/tool",
        }
        data.update(overrides or {})
        encoded = json.dumps(data).encode("utf-8")
        stdin = types.SimpleNamespace(buffer=io.BytesIO(encoded))
        with mock.patch.object(_child.sys, "stdin", stdin):
            return _child._payload()

    def test_valid_payload_is_revalidated(self):
        decoded = self.payload({"env": {"A": "b"}})

        self.assertEqual(decoded["executable"], "/bin/tool")
        self.assertEqual(decoded["env"], {"A": "b"})

    def test_boolean_version_empty_argv_and_traversal_are_rejected(self):
        cases = (
            {"schema_version": True},
            {"argv": [""]},
            {"executable": "/bin/../tool"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.payload(overrides)

    def test_duplicate_json_keys_are_rejected(self):
        encoded = (
            b'{"schema_version":1,"schema_version":1,"rootfs":"/r",'
            b'"argv":["/x"],"env":{},"hostname":"minibox",'
            b'"executable":"/x"}'
        )
        stdin = types.SimpleNamespace(buffer=io.BytesIO(encoded))

        with mock.patch.object(_child.sys, "stdin", stdin):
            with self.assertRaises(ValueError):
                _child._payload()

    def test_status_descriptor_must_be_a_pipe_and_becomes_close_on_exec(self):
        read_descriptor, write_descriptor = os.pipe()
        self.addCleanup(os.close, read_descriptor)
        self.addCleanup(os.close, write_descriptor)
        os.set_inheritable(write_descriptor, True)
        with mock.patch.dict(
            os.environ,
            {"MINIBOX_STATUS_FD": str(write_descriptor)},
            clear=True,
        ):
            self.assertEqual(_child._status_descriptor(), write_descriptor)
        self.assertFalse(os.get_inheritable(write_descriptor))

        with tempfile.TemporaryFile() as regular:
            with mock.patch.dict(
                os.environ,
                {"MINIBOX_STATUS_FD": str(regular.fileno())},
                clear=True,
            ):
                with self.assertRaises(ValueError):
                    _child._status_descriptor()


if __name__ == "__main__":
    unittest.main()
