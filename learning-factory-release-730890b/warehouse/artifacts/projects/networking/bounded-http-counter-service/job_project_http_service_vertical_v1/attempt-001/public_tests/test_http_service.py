from __future__ import annotations

import json
import socket
import unittest

from http_service import CounterApp, HTTPParser, Request, Server, ServiceConfig


def request_bytes(
    method: str,
    target: str,
    body: bytes = b"",
    *,
    headers: dict[str, str] | None = None,
    close: bool = True,
) -> bytes:
    values = {"Host": "exercise.local", **(headers or {})}
    if body or method in {"PUT", "POST"}:
        values.setdefault("Content-Length", str(len(body)))
    values["Connection"] = "close" if close else "keep-alive"
    head = f"{method} {target} HTTP/1.1\r\n" + "".join(
        f"{name}: {value}\r\n" for name, value in values.items()
    )
    return head.encode("ascii") + b"\r\n" + body


def exchange(address: tuple[str, int], payload: bytes) -> bytes:
    with socket.create_connection(address, timeout=2.0) as client:
        client.settimeout(2.0)
        client.sendall(payload)
        chunks: list[bytes] = []
        while True:
            data = client.recv(65536)
            if not data:
                return b"".join(chunks)
            chunks.append(data)


def response_json(raw: bytes) -> tuple[int, dict[str, str], object]:
    head, body = raw.split(b"\r\n\r\n", 1)
    lines = head.decode("latin-1").split("\r\n")
    status = int(lines[0].split(" ", 2)[1])
    headers = {name.lower(): value.strip() for name, value in (
        line.split(":", 1) for line in lines[1:]
    )}
    assert int(headers["content-length"]) == len(body)
    return status, headers, json.loads(body) if body else None


class PublicParserTests(unittest.TestCase):
    def test_fragmented_request_is_not_emitted_early(self) -> None:
        parser = HTTPParser()
        wire = request_bytes("PUT", "/v1/counters/jobs", b'{"value":7}', headers={"Content-Type": "application/json"})
        observed = []
        for byte in wire:
            observed.extend(parser.feed(bytes([byte])))
        self.assertEqual(1, len(observed))
        self.assertEqual(b'{"value":7}', observed[0].body)

    def test_two_pipelined_requests_are_preserved(self) -> None:
        parser = HTTPParser()
        requests = parser.feed(
            request_bytes("GET", "/healthz", close=False)
            + request_bytes("GET", "/metrics")
        )
        self.assertEqual(["/healthz", "/metrics"], [item.target for item in requests])


class PublicApplicationTests(unittest.TestCase):
    def test_idempotent_increment_is_applied_once(self) -> None:
        app = CounterApp()
        request = Request(
            "POST",
            "/v1/counters/builds/increment",
            "HTTP/1.1",
            {
                "host": "exercise.local",
                "content-length": "11",
                "content-type": "application/json",
                "idempotency-key": "build-42",
            },
            b'{"delta":3}',
        )
        first = app.handle(request)
        second = app.handle(request)
        self.assertEqual(first, second)
        fetched = app.handle(Request("GET", "/v1/counters/builds", "HTTP/1.1", {"host": "exercise.local"}, b""))
        self.assertEqual(3, json.loads(fetched.body)["value"])


class PublicNetworkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = Server(ServiceConfig(worker_count=2, read_timeout=0.2))
        self.server.start()

    def tearDown(self) -> None:
        self.server.close()

    def test_health_endpoint(self) -> None:
        status, headers, body = response_json(
            exchange(self.server.address, request_bytes("GET", "/healthz"))
        )
        self.assertEqual(200, status)
        self.assertEqual("close", headers["connection"])
        self.assertEqual({"status": "ok"}, body)

    def test_put_then_get_exposes_version(self) -> None:
        status, _, created = response_json(
            exchange(
                self.server.address,
                request_bytes(
                    "PUT",
                    "/v1/counters/releases",
                    b'{"value":9}',
                    headers={"Content-Type": "application/json"},
                ),
            )
        )
        self.assertEqual(201, status)
        self.assertEqual(1, created["version"])
        status, headers, fetched = response_json(
            exchange(self.server.address, request_bytes("GET", "/v1/counters/releases"))
        )
        self.assertEqual(200, status)
        self.assertEqual('"1"', headers["etag"])
        self.assertEqual(9, fetched["value"])


if __name__ == "__main__":
    unittest.main()
