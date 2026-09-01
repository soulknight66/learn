from __future__ import annotations

import unittest

from minibox.errors import InvalidIdentifier, InvalidSpec, InvalidTransition
from minibox.models import ContainerSpec, ContainerState, validate_identifier, validate_transition


class IdentifierTests(unittest.TestCase):
    def test_accepts_boundary_and_punctuation(self) -> None:
        self.assertEqual(validate_identifier("a"), "a")
        value = "a" + "0._-" * 15 + "xyz"
        self.assertEqual(len(value), 64)
        self.assertEqual(validate_identifier(value), value)

    def test_rejects_noncanonical_identifiers(self) -> None:
        for value in ("", "Upper", "-leading", "a/b", "two words", "café", True, b"bytes"):
            with self.subTest(value=value), self.assertRaises(InvalidIdentifier):
                validate_identifier(value)


class SpecTests(unittest.TestCase):
    def test_round_trip_copies_mutable_inputs(self) -> None:
        source_env = {"MODE": "test"}
        spec = ContainerSpec("demo.1", "base", ["/bin/echo", "hi"], source_env, "/work")  # type: ignore[arg-type]
        source_env["MODE"] = "changed"
        self.assertEqual(spec.env["MODE"], "test")
        self.assertEqual(ContainerSpec.from_dict(spec.to_dict()), spec)

    def test_rejects_invalid_payload_fields(self) -> None:
        cases = (
            {"argv": ()},
            {"argv": ("",)},
            {"argv": ("ok\x00bad",)},
            {"argv": ("ok",), "env": {"BAD-NAME": "x"}},
            {"argv": ("ok",), "env": {"GOOD": "x\x00y"}},
            {"argv": ("ok",), "working_dir": "relative"},
            {"argv": ("ok",), "working_dir": "/a/../b"},
            {"argv": ("ok",), "network": 1},
        )
        for changes in cases:
            values = {
                "container_id": "demo",
                "image_id": "base",
                "argv": ("ok",),
                "env": {},
                "working_dir": "/",
                "network": False,
            }
            values.update(changes)
            with self.subTest(values=values), self.assertRaises(InvalidSpec):
                ContainerSpec(**values)  # type: ignore[arg-type]


class TransitionTests(unittest.TestCase):
    def test_representative_allowed_edges(self) -> None:
        validate_transition(ContainerState.CREATED, ContainerState.RUNNING)
        validate_transition(ContainerState.RUNNING, ContainerState.EXITED)
        validate_transition(ContainerState.EXITED, ContainerState.RUNNING)

    def test_rejects_self_and_skipped_edges(self) -> None:
        for current, target in (
            (ContainerState.CREATED, ContainerState.CREATED),
            (ContainerState.CREATED, ContainerState.EXITED),
            (ContainerState.DELETED, ContainerState.RUNNING),
        ):
            with self.subTest(current=current, target=target), self.assertRaises(InvalidTransition):
                validate_transition(current, target)


if __name__ == "__main__":
    unittest.main()
