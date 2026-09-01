from __future__ import annotations

import json
import math
import re
from typing import Any


MAX_STORED_JSON_BYTES = 16 * 1024 * 1024
MAX_JSON_NESTING_DEPTH = 128
MAX_JSON_TOKENS = 250_000
MAX_JSON_NODES = 100_000
MAX_JSON_STRING_CHARACTERS = 1024 * 1024
MAX_JSON_NUMBER_CHARACTERS = 512
MAX_JSON_INTEGER_DIGITS = 256

_NUMBER_RE = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")
_NUMBER_CHARACTERS = frozenset("-+0123456789.eE")
_NONFINITE_CONSTANTS = ("-Infinity", "Infinity", "NaN")


class StrictJsonError(ValueError):
    """JSON bytes are malformed, ambiguous, non-finite, or unbounded."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise StrictJsonError(f"duplicate JSON object key: {key}")
        value[key] = item
    return value


def _reject_constant(value: str) -> object:
    raise StrictJsonError(f"non-standard JSON numeric constant: {value}")


def _finite_float(value: str) -> float:
    if len(value) > MAX_JSON_NUMBER_CHARACTERS:
        raise StrictJsonError("JSON number literal exceeds its character limit")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise StrictJsonError("JSON number is not finite")
    return parsed


def _bounded_int(value: str) -> int:
    digits = value[1:] if value.startswith("-") else value
    if len(digits) > MAX_JSON_INTEGER_DIGITS:
        raise StrictJsonError("JSON integer literal exceeds its digit limit")
    return int(value)


def _bounded_lexical_preflight(document: str) -> None:
    """Apply deterministic resource limits before the recursive JSON decoder.

    The standard decoder's integer and nesting limits inherit mutable interpreter
    globals.  This small string-aware lexer does not attempt semantic decoding;
    it establishes hard bounds and leaves complete grammar validation to
    ``json.loads``.
    """

    stack: list[str] = []
    tokens = 0
    nodes = 0
    index = 0
    length = len(document)

    def count_token(*, node: bool = False) -> None:
        nonlocal tokens, nodes
        tokens += 1
        if tokens > MAX_JSON_TOKENS:
            raise StrictJsonError("JSON document exceeds its token limit")
        if node:
            nodes += 1
            if nodes > MAX_JSON_NODES:
                raise StrictJsonError("JSON document exceeds its node limit")

    while index < length:
        character = document[index]
        if character in " \t\r\n":
            index += 1
            continue
        if character in "[{":
            count_token(node=True)
            stack.append(character)
            if len(stack) > MAX_JSON_NESTING_DEPTH:
                raise StrictJsonError("JSON document exceeds its nesting limit")
            index += 1
            continue
        if character in "]}":
            count_token()
            expected = "[" if character == "]" else "{"
            if not stack or stack[-1] != expected:
                raise StrictJsonError("JSON document has mismatched structure")
            stack.pop()
            index += 1
            continue
        if character in ",:":
            count_token()
            index += 1
            continue
        if character == '"':
            start = index
            index += 1
            while index < length:
                current = document[index]
                if current == '"':
                    index += 1
                    break
                if current == "\\":
                    index += 2
                else:
                    index += 1
                if index - start - 1 > MAX_JSON_STRING_CHARACTERS:
                    raise StrictJsonError(
                        "JSON string token exceeds its character limit"
                    )
            else:
                raise StrictJsonError("JSON document contains an unterminated string")
            count_token(node=True)
            continue
        matched_constant = next(
            (
                value
                for value in _NONFINITE_CONSTANTS
                if document.startswith(value, index)
            ),
            None,
        )
        if matched_constant is not None:
            raise StrictJsonError(
                f"non-standard JSON numeric constant: {matched_constant}"
            )
        if character == "-" or character.isdigit():
            end = index
            while end < length and document[end] in _NUMBER_CHARACTERS:
                if end - index >= MAX_JSON_NUMBER_CHARACTERS:
                    raise StrictJsonError(
                        "JSON number literal exceeds its character limit"
                    )
                end += 1
            literal = document[index:end]
            if _NUMBER_RE.fullmatch(literal) is None:
                raise StrictJsonError("JSON document contains an invalid number")
            count_token(node=True)
            index = end
            continue
        literal = next(
            (
                value
                for value in ("true", "false", "null")
                if document.startswith(value, index)
            ),
            None,
        )
        if literal is None:
            raise StrictJsonError("JSON document contains an invalid token")
        count_token(node=True)
        index += len(literal)

    if stack:
        raise StrictJsonError("JSON document has incomplete structure")


def _reject_unpaired_surrogates(value: Any) -> None:
    """Reject surrogate code points produced by escaped JSON strings."""

    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            if any(0xD800 <= ord(character) <= 0xDFFF for character in item):
                raise StrictJsonError("JSON text contains an unpaired surrogate")
        elif isinstance(item, dict):
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)


def strict_json_loads(
    raw: str | bytes,
    *,
    max_bytes: int = MAX_STORED_JSON_BYTES,
) -> Any:
    """Decode bounded JSON while rejecting duplicate keys at every depth."""

    if type(max_bytes) is not int or max_bytes < 1:
        raise StrictJsonError("JSON byte limit must be a positive integer")
    if type(raw) not in {str, bytes}:
        raise StrictJsonError("JSON input must be text or bytes")
    try:
        if type(raw) is str:
            # Every Python character occupies at least one UTF-8 byte.  This
            # cheap lower bound prevents a huge exact string from being copied
            # by encode() merely to discover that it is already oversized.
            if len(raw) > max_bytes:
                raise StrictJsonError("JSON input exceeds its byte limit")
            encoded_size = len(raw.encode("utf-8"))
            document = raw
        else:
            encoded_size = len(raw)
        if encoded_size > max_bytes:
            raise StrictJsonError("JSON input exceeds its byte limit")
        if type(raw) is bytes:
            document = raw.decode("utf-8")
        _bounded_lexical_preflight(document)
        value = json.loads(
            document,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
            parse_float=_finite_float,
            parse_int=_bounded_int,
        )
        _reject_unpaired_surrogates(value)
        return value
    except (
        UnicodeError,
        json.JSONDecodeError,
        ValueError,
        RecursionError,
    ) as error:
        raise StrictJsonError(str(error)) from error
