"""Strict parsing and validation for the untrusted JSON process boundary."""

import json
import re
from typing import Any, Dict, FrozenSet, Iterable, Tuple

from .models import Action, AuthorizationRequest, Principal, Resource, Role

MAX_INPUT_BYTES = 4096
JSON_WHITESPACE = frozenset(" \t\r\n")
IDENTIFIER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")

TOP_LEVEL_KEYS = frozenset({"principal", "action", "resource"})
PRINCIPAL_KEYS = frozenset({"subject_id", "tenant_id", "role"})
RESOURCE_KEYS = frozenset({"resource_id", "tenant_id", "owner_id"})


class InvalidInput(ValueError):
    """The external request is malformed or outside the declared schema."""


class _DuplicateKey(ValueError):
    pass


class _NonJsonConstant(ValueError):
    pass


def _object_without_duplicates(pairs: Iterable[Tuple[str, Any]]) -> Dict[str, Any]:
    result = {}  # type: Dict[str, Any]
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey
        result[key] = value
    return result


def _reject_non_json_constant(_value: str) -> None:
    raise _NonJsonConstant


_DECODER = json.JSONDecoder(
    object_pairs_hook=_object_without_duplicates,
    parse_constant=_reject_non_json_constant,
    strict=True,
)


def _decode_one_document(raw: bytes) -> Any:
    if not raw or len(raw) > MAX_INPUT_BYTES:
        raise InvalidInput from None

    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise InvalidInput from None

    start = 0
    while start < len(text) and text[start] in JSON_WHITESPACE:
        start += 1
    if start == len(text):
        raise InvalidInput from None

    try:
        value, end = _DECODER.raw_decode(text, start)
    except (json.JSONDecodeError, _DuplicateKey, _NonJsonConstant, RecursionError, ValueError):
        raise InvalidInput from None

    if any(character not in JSON_WHITESPACE for character in text[end:]):
        raise InvalidInput from None
    return value


def _has_exact_keys(value: Any, expected: FrozenSet[str]) -> bool:
    return type(value) is dict and frozenset(value) == expected


def _all_strings(value: Dict[str, Any]) -> bool:
    return all(type(field_value) is str for field_value in value.values())


def _valid_identifiers(values: Iterable[str]) -> bool:
    return all(IDENTIFIER_RE.fullmatch(value) is not None for value in values)


def parse_request(raw: bytes) -> AuthorizationRequest:
    """Parse bytes into validated domain values or raise ``InvalidInput``."""

    document = _decode_one_document(raw)
    if not _has_exact_keys(document, TOP_LEVEL_KEYS):
        raise InvalidInput from None

    principal_data = document["principal"]
    resource_data = document["resource"]
    action_data = document["action"]

    if not _has_exact_keys(principal_data, PRINCIPAL_KEYS):
        raise InvalidInput from None
    if not _has_exact_keys(resource_data, RESOURCE_KEYS):
        raise InvalidInput from None
    if not _all_strings(principal_data) or not _all_strings(resource_data):
        raise InvalidInput from None
    if type(action_data) is not str:
        raise InvalidInput from None

    identifiers = (
        principal_data["subject_id"],
        principal_data["tenant_id"],
        resource_data["resource_id"],
        resource_data["tenant_id"],
        resource_data["owner_id"],
    )
    if not _valid_identifiers(identifiers):
        raise InvalidInput from None

    try:
        role = Role(principal_data["role"])
        action = Action(action_data)
    except ValueError:
        raise InvalidInput from None

    return AuthorizationRequest(
        principal=Principal(
            subject_id=principal_data["subject_id"],
            tenant_id=principal_data["tenant_id"],
            role=role,
        ),
        action=action,
        resource=Resource(
            resource_id=resource_data["resource_id"],
            tenant_id=resource_data["tenant_id"],
            owner_id=resource_data["owner_id"],
        ),
    )
