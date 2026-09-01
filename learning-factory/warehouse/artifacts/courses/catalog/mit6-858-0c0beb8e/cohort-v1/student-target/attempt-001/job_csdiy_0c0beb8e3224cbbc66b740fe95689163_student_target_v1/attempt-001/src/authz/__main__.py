"""Command-line adapter for exercising the authorization boundary."""

import json
import sys

from .parsing import MAX_INPUT_BYTES, InvalidInput, parse_request
from .policy import authorize

INVALID_RESPONSE = '{"error":"invalid_input"}\n'


def _read_bounded(stream) -> bytes:
    """Read through byte 4097, tolerating short reads without unbounded buffering."""

    chunks = []
    remaining = MAX_INPUT_BYTES + 1
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def main() -> int:
    raw = _read_bounded(sys.stdin.buffer)
    try:
        request = parse_request(raw)
    except InvalidInput:
        sys.stdout.write(INVALID_RESPONSE)
        return 2

    decision = authorize(request)
    allowed_json = "true" if decision.allowed else "false"
    reason_json = json.dumps(decision.reason, ensure_ascii=True)
    sys.stdout.write(
        '{"allowed":' + allowed_json + ',"reason":' + reason_json + "}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
