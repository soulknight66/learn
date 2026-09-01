"""Strict parser and process-boundary tests."""

import copy
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from typing import Dict

from authz import Action, Role
from authz.__main__ import _read_bounded
from authz.parsing import MAX_INPUT_BYTES, InvalidInput, parse_request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
PYTHON_EXECUTABLE = sys.executable or shutil.which("python3")
if PYTHON_EXECUTABLE is None:
    raise RuntimeError("python3 is required for CLI boundary tests")


def valid_document() -> Dict[str, object]:
    return {
        "principal": {
            "subject_id": "subject-a",
            "tenant_id": "tenant-a",
            "role": "member",
        },
        "action": "read",
        "resource": {
            "resource_id": "resource-a",
            "tenant_id": "tenant-a",
            "owner_id": "subject-a",
        },
    }


def encoded(document: object) -> bytes:
    return json.dumps(document, separators=(",", ":")).encode("utf-8")


def set_path(document, path, value):
    target = document
    for component in path[:-1]:
        if type(target) is not dict:
            raise AssertionError("test fixture path did not address an object")
        target = target[component]
    if type(target) is not dict:
        raise AssertionError("test fixture path did not address a field")
    target[path[-1]] = value


class StrictParserTests(unittest.TestCase):
    def assert_invalid(self, raw: bytes) -> None:
        with self.assertRaises(InvalidInput):
            parse_request(raw)

    def test_valid_request_becomes_typed_domain_values(self) -> None:
        request = parse_request(b" \t\r\n" + encoded(valid_document()) + b" \t\r\n")
        self.assertIs(request.principal.role, Role.MEMBER)
        self.assertIs(request.action, Action.READ)
        self.assertEqual("resource-a", request.resource.resource_id)

    def test_empty_invalid_json_and_non_object_roots_are_rejected(self) -> None:
        cases = (b"", b" \t\r\n", b"{", b"not-json", b"[]", b"null", b'"object"')
        for raw in cases:
            with self.subTest(raw=raw):
                self.assert_invalid(raw)

    def test_invalid_utf8_and_non_json_constants_are_rejected(self) -> None:
        for raw in (b"\xff", b'{"principal":NaN}', b'{"principal":Infinity}'):
            with self.subTest(raw=raw):
                self.assert_invalid(raw)

    def test_duplicate_keys_at_every_object_level_are_rejected(self) -> None:
        duplicates = (
            b'{"principal":{"subject_id":"a","tenant_id":"t","role":"member"},"action":"read","action":"delete","resource":{"resource_id":"r","tenant_id":"t","owner_id":"a"}}',
            b'{"principal":{"subject_id":"a","subject_id":"b","tenant_id":"t","role":"member"},"action":"read","resource":{"resource_id":"r","tenant_id":"t","owner_id":"a"}}',
            b'{"principal":{"subject_id":"a","tenant_id":"t","role":"member"},"action":"read","resource":{"resource_id":"r","resource_id":"s","tenant_id":"t","owner_id":"a"}}',
        )
        for raw in duplicates:
            with self.subTest(raw=raw):
                self.assert_invalid(raw)

    def test_missing_and_extra_keys_are_rejected_at_each_level(self) -> None:
        object_paths = ((), ("principal",), ("resource",))
        for path in object_paths:
            baseline = valid_document()
            target = baseline
            for component in path:
                nested = target[component]
                self.assertIs(type(nested), dict)
                target = nested
            removed_key = next(iter(target))
            missing = copy.deepcopy(baseline)
            missing_target = missing
            for component in path:
                missing_target = missing_target[component]
            del missing_target[removed_key]
            extra = copy.deepcopy(baseline)
            extra_target = extra
            for component in path:
                extra_target = extra_target[component]
            extra_target["unexpected"] = "value"
            with self.subTest(path=path, kind="missing"):
                self.assert_invalid(encoded(missing))
            with self.subTest(path=path, kind="extra"):
                self.assert_invalid(encoded(extra))

    def test_every_field_rejects_non_string_json_types(self) -> None:
        field_paths = (
            ("principal", "subject_id"),
            ("principal", "tenant_id"),
            ("principal", "role"),
            ("action",),
            ("resource", "resource_id"),
            ("resource", "tenant_id"),
            ("resource", "owner_id"),
        )
        wrong_types = (None, 7, True, [], {})
        for path, wrong_value in itertools.product(field_paths, wrong_types):
            document = valid_document()
            set_path(document, path, wrong_value)
            with self.subTest(path=path, value_type=type(wrong_value).__name__):
                self.assert_invalid(encoded(document))

    def test_identifiers_must_match_declared_ascii_grammar(self) -> None:
        identifier_paths = (
            ("principal", "subject_id"),
            ("principal", "tenant_id"),
            ("resource", "resource_id"),
            ("resource", "tenant_id"),
            ("resource", "owner_id"),
        )
        invalid_identifiers = ("", ".leading", "-leading", "_leading", "has space", "a/b", "é", "a" * 65)
        for path, bad_identifier in itertools.product(identifier_paths, invalid_identifiers):
            document = valid_document()
            set_path(document, path, bad_identifier)
            with self.subTest(path=path, identifier=bad_identifier):
                self.assert_invalid(encoded(document))

    def test_unknown_role_and_action_are_rejected(self) -> None:
        cases = (("principal", "role", "owner"), ("principal", "role", "Admin"), ("action", "execute"), ("action", "Read"))
        for case in cases:
            document = valid_document()
            if case[0] == "principal":
                set_path(document, ("principal", case[1]), case[2])
            else:
                set_path(document, ("action",), case[1])
            with self.subTest(case=case):
                self.assert_invalid(encoded(document))

    def test_trailing_non_whitespace_and_concatenated_documents_are_rejected(self) -> None:
        raw = encoded(valid_document())
        for suffix in (b"x", b" {}", b"\x00", "\u00a0".encode("utf-8")):
            with self.subTest(suffix=suffix):
                self.assert_invalid(raw + suffix)

    def test_size_limit_counts_bytes_and_accepts_exact_limit(self) -> None:
        raw = encoded(valid_document())
        exactly_limit = raw + (b" " * (MAX_INPUT_BYTES - len(raw)))
        self.assertEqual(MAX_INPUT_BYTES, len(exactly_limit))
        parse_request(exactly_limit)
        self.assert_invalid(exactly_limit + b" ")

    def test_deeply_nested_malformed_input_has_controlled_rejection(self) -> None:
        raw = (b"[" * 1200) + b"0" + (b"]" * 1200)
        self.assertLess(len(raw), MAX_INPUT_BYTES)
        self.assert_invalid(raw)


class ShortReadStream:
    def __init__(self, raw, chunk_size):
        self.raw = raw
        self.chunk_size = chunk_size
        self.offset = 0

    def read(self, requested):
        count = min(requested, self.chunk_size, len(self.raw) - self.offset)
        if count <= 0:
            return b""
        result = self.raw[self.offset : self.offset + count]
        self.offset += count
        return result


class BoundedReadTests(unittest.TestCase):
    def test_short_reads_are_joined_until_eof(self) -> None:
        raw = encoded(valid_document())
        stream = ShortReadStream(raw, 3)
        self.assertEqual(raw, _read_bounded(stream))

    def test_short_reads_stop_after_overflow_detection_byte(self) -> None:
        stream = ShortReadStream(b"x" * 5000, 7)
        result = _read_bounded(stream)
        self.assertEqual(MAX_INPUT_BYTES + 1, len(result))
        self.assertEqual(MAX_INPUT_BYTES + 1, stream.offset)


class CliBoundaryTests(unittest.TestCase):
    def run_cli(self, raw: bytes):
        environment = {"PYTHONPATH": str(SRC_ROOT)}
        return subprocess.run(
            [PYTHON_EXECUTABLE, "-m", "authz"],
            cwd=PROJECT_ROOT,
            env=environment,
            input=raw,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=3,
            check=False,
            start_new_session=True,
        )

    def test_cli_allow_has_exact_shape_and_success_status(self) -> None:
        completed = self.run_cli(encoded(valid_document()))
        self.assertEqual(0, completed.returncode)
        self.assertEqual(b'{"allowed":true,"reason":"allow_owner"}\n', completed.stdout)
        self.assertEqual(b"", completed.stderr)
        self.assertEqual({"allowed", "reason"}, set(json.loads(completed.stdout)))

    def test_cli_policy_denial_is_a_successful_decision(self) -> None:
        document = valid_document()
        set_path(document, ("principal", "role"), "auditor")
        set_path(document, ("action",), "delete")
        completed = self.run_cli(encoded(document))
        self.assertEqual(0, completed.returncode)
        self.assertEqual(
            b'{"allowed":false,"reason":"deny_insufficient_privilege"}\n',
            completed.stdout,
        )
        self.assertEqual(b"", completed.stderr)

    def test_cli_malformed_input_is_generic_and_status_two(self) -> None:
        missing_action = valid_document()
        del missing_action["action"]
        extra_key = valid_document()
        extra_key["unexpected"] = "value"
        wrong_type = valid_document()
        wrong_type["action"] = None
        invalid_identifier = valid_document()
        invalid_identifier["principal"]["subject_id"] = ".subject"  # type: ignore[index]
        unknown_role = valid_document()
        unknown_role["principal"]["role"] = "owner"  # type: ignore[index]
        unknown_action = valid_document()
        unknown_action["action"] = "execute"
        valid_raw = encoded(valid_document())
        malformed_cases = (
            ("empty", b""),
            ("invalid_json", b"{"),
            ("invalid_utf8", b"\xff"),
            (
                "duplicate_key",
                b'{"principal":{"subject_id":"a","subject_id":"b","tenant_id":"t","role":"member"},"action":"read","resource":{"resource_id":"r","tenant_id":"t","owner_id":"a"}}',
            ),
            ("missing_key", encoded(missing_action)),
            ("extra_key", encoded(extra_key)),
            ("wrong_type", encoded(wrong_type)),
            ("invalid_identifier", encoded(invalid_identifier)),
            ("unknown_role", encoded(unknown_role)),
            ("unknown_action", encoded(unknown_action)),
            ("trailing_non_whitespace", valid_raw + b"x"),
            (
                "oversized",
                valid_raw + (b" " * (MAX_INPUT_BYTES + 1 - len(valid_raw))),
            ),
        )
        for label, raw in malformed_cases:
            with self.subTest(input_class=label):
                completed = self.run_cli(raw)
                self.assertEqual(2, completed.returncode)
                self.assertEqual(b'{"error":"invalid_input"}\n', completed.stdout)
                self.assertEqual(b"", completed.stderr)


if __name__ == "__main__":
    unittest.main()
