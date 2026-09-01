from __future__ import annotations

from http_core import HTTPParser


def main() -> int:
    parser = HTTPParser()
    head = (
        b"PUT /v1/counters/partial HTTP/1.1\r\n"
        b"Host: debug.local\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: 13\r\n\r\n"
    )
    first = parser.feed(head + b'{"val')
    assert first == [], "parser emitted a request before Content-Length bytes arrived"
    second = parser.feed(b'ue":123}')
    assert len(second) == 1
    assert second[0].body == b'{"value":123}'
    print("fragmented body remained buffered until complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
