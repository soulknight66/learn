from __future__ import annotations

import unittest

from minibox.errors import InvalidIdentifier, InvalidSpec, InvalidTransition
from minibox.models import ContainerSpec, ContainerState, validate_identifier, validate_transition


class ExhaustiveModelTests(unittest.TestCase):
    def test_identifier_lengths(self) -> None:
        self.assertEqual(validate_identifier("a" * 64), "a" * 64)
        for value in ("a" * 65, ".dot", "_under", "-dash", None, 1, 1.5):
            with self.subTest(value=value), self.assertRaises(InvalidIdentifier):
                validate_identifier(value)

    def test_every_transition_pair(self) -> None:
        allowed = {
            (ContainerState.CREATED, ContainerState.RUNNING),
            (ContainerState.CREATED, ContainerState.DELETED),
            (ContainerState.RUNNING, ContainerState.EXITED),
            (ContainerState.RUNNING, ContainerState.FAILED),
            (ContainerState.EXITED, ContainerState.RUNNING),
            (ContainerState.EXITED, ContainerState.DELETED),
            (ContainerState.FAILED, ContainerState.RUNNING),
            (ContainerState.FAILED, ContainerState.DELETED),
        }
        for current in ContainerState:
            for target in ContainerState:
                with self.subTest(current=current, target=target):
                    if (current, target) in allowed:
                        validate_transition(current, target)
                    else:
                        with self.assertRaises(InvalidTransition):
                            validate_transition(current, target)

    def test_normalized_working_directory_and_frozen_environment(self) -> None:
        for workdir in ("//srv", "/srv/", "/srv//app", "/srv/./app", 3):
            with self.subTest(workdir=workdir), self.assertRaises(InvalidSpec):
                ContainerSpec("one", "base", ("run",), working_dir=workdir)  # type: ignore[arg-type]

        env = {"ZED": "last", "ALPHA": "first"}
        spec = ContainerSpec("one", "base", ("run",), env)
        env.clear()
        self.assertEqual(list(spec.env), ["ALPHA", "ZED"])
        with self.assertRaises(TypeError):
            spec.env["NEW"] = "value"  # type: ignore[index]

    def test_serialized_shape_errors_are_domain_errors(self) -> None:
        for value in ({}, {"container_id": "one", "image_id": "base", "argv": "run"}, []):
            with self.subTest(value=value), self.assertRaises(InvalidSpec):
                ContainerSpec.from_dict(value)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
