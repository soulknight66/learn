import math
import unittest

from minictr.errors import ValidationError
from minictr.spec import ContainerSpec


def valid_spec():
    return {
        "id": "demo_1",
        "rootfs": "/tmp/tinyctr-demo",
        "command": ["/bin/echo", "hello; not a shell"],
        "hostname": "demo-1",
        "env": {"LANG": "C", "MESSAGE": "hello world"},
        "timeout_seconds": 2,
        "readonly_root": True,
        "network": False,
    }


class ContainerSpecTests(unittest.TestCase):
    def test_normalizes_to_immutable_values(self):
        raw = valid_spec()
        spec = ContainerSpec.from_mapping(raw)
        raw["command"].append("changed")
        raw["env"]["LANG"] = "changed"
        self.assertEqual(spec.command, ("/bin/echo", "hello; not a shell"))
        self.assertEqual(spec.env["LANG"], "C")

    def test_to_mapping_returns_fresh_containers(self):
        spec = ContainerSpec.from_mapping(valid_spec())
        first = spec.to_mapping()
        first["command"].append("mutated")
        first["env"]["LANG"] = "mutated"
        self.assertEqual(spec.to_mapping()["command"], ["/bin/echo", "hello; not a shell"])
        self.assertEqual(spec.to_mapping()["env"]["LANG"], "C")

    def test_rejects_unknown_field(self):
        raw = valid_spec()
        raw["privileged"] = True
        with self.assertRaises(ValidationError):
            ContainerSpec.from_mapping(raw)

    def test_rejects_boolean_and_nonfinite_timeouts(self):
        for bad in (True, math.inf, math.nan, 0.01, 301):
            with self.subTest(timeout=bad):
                raw = valid_spec()
                raw["timeout_seconds"] = bad
                with self.assertRaises(ValidationError):
                    ContainerSpec.from_mapping(raw)

    def test_rejects_invalid_environment_name(self):
        raw = valid_spec()
        raw["env"] = {"BAD-NAME": "x"}
        with self.assertRaises(ValidationError):
            ContainerSpec.from_mapping(raw)


if __name__ == "__main__":
    unittest.main()
