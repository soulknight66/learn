from __future__ import annotations

import argparse
import random

from http_service import HTTPParser, ProtocolError


VALID = b"PUT /v1/counters/parser HTTP/1.1\r\nHost: fuzz.local\r\nContent-Type: application/json\r\nContent-Length: 12\r\n\r\n{\"value\":41}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260830)
    parser.add_argument("--iterations", type=int, default=120)
    args = parser.parse_args()
    if args.iterations < 1 or args.iterations > 2000:
        parser.error("iterations must be between 1 and 2000")
    randomizer = random.Random(args.seed)
    for _ in range(args.iterations):
        subject = HTTPParser(max_header_bytes=512, max_body_bytes=64)
        cursor = 0
        requests = []
        while cursor < len(VALID):
            width = randomizer.randint(1, 9)
            requests.extend(subject.feed(VALID[cursor : cursor + width]))
            cursor += width
        assert len(requests) == 1 and requests[0].body == b'{"value":41}'
    invalid = [
        b"GET / HTTP/1.1\r\n\r\n",
        b"GET / HTTP/1.0\r\nHost: x\r\n\r\n",
        b"GET / HTTP/1.1\r\nHost: x\r\nHost: y\r\n\r\n",
        b"GET / HTTP/1.1\r\n Host: x\r\n\r\n",
        b"POST / HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\n\r\n",
        b"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: +1\r\n\r\nx",
    ]
    for payload in invalid:
        try:
            HTTPParser().feed(payload)
        except ProtocolError:
            pass
        else:
            raise AssertionError(f"invalid request accepted: {payload!r}")
    print(f"parser adversary passed seed={args.seed} iterations={args.iterations}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
