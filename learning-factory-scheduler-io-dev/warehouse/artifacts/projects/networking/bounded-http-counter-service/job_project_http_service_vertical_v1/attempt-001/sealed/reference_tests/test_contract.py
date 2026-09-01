from __future__ import annotations

import json
import socket
import threading
import time
import unittest

from http_service import HTTPParser, ProtocolError, Server, ServiceConfig


def wire(
    method: str,
    target: str,
    body: bytes = b"",
    *,
    headers: dict[str, str] | None = None,
    close: bool = True,
) -> bytes:
    values = {"Host": "hidden.local", **(headers or {})}
    if body or method in {"PUT", "POST"}:
        values.setdefault("Content-Length", str(len(body)))
    values["Connection"] = "close" if close else "keep-alive"
    return (
        f"{method} {target} HTTP/1.1\r\n"
        + "".join(f"{key}: {value}\r\n" for key, value in values.items())
        + "\r\n"
    ).encode("ascii") + body


def exchange(address: tuple[str, int], payload: bytes) -> bytes:
    with socket.create_connection(address, timeout=2.0) as client:
        client.settimeout(2.0)
        client.sendall(payload)
        output = bytearray()
        while True:
            chunk = client.recv(65536)
            if not chunk:
                return bytes(output)
            output.extend(chunk)


def parse_one(raw: bytes) -> tuple[int, dict[str, str], object]:
    head, body = raw.split(b"\r\n\r\n", 1)
    lines = head.decode("latin-1").split("\r\n")
    status = int(lines[0].split(" ", 2)[1])
    headers = dict(line.split(": ", 1) for line in lines[1:])
    return status, headers, json.loads(body) if body else None


def read_one(client: socket.socket) -> bytes:
    raw = bytearray()
    while b"\r\n\r\n" not in raw:
        chunk = client.recv(65536)
        if not chunk:
            raise AssertionError("connection closed before response headers")
        raw.extend(chunk)
    marker = raw.index(b"\r\n\r\n") + 4
    head = bytes(raw[: marker - 4]).decode("latin-1")
    headers = dict(line.split(": ", 1) for line in head.split("\r\n")[1:])
    expected = marker + int(headers["content-length"])
    while len(raw) < expected:
        chunk = client.recv(65536)
        if not chunk:
            raise AssertionError("connection closed before response body")
        raw.extend(chunk)
    return bytes(raw[:expected])


class HiddenParserTests(unittest.TestCase):
    def assert_protocol_status(self, payload: bytes, status: int) -> None:
        with self.assertRaises(ProtocolError) as caught:
            HTTPParser(max_header_bytes=256, max_body_bytes=16).feed(payload)
        self.assertEqual(status, caught.exception.status)

    def test_missing_host_is_rejected(self) -> None:
        self.assert_protocol_status(b"GET / HTTP/1.1\r\n\r\n", 400)

    def test_duplicate_content_length_is_rejected(self) -> None:
        self.assert_protocol_status(
            b"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: 1\r\nContent-Length: 2\r\n\r\nx",
            400,
        )

    def test_transfer_encoding_is_rejected(self) -> None:
        self.assert_protocol_status(
            b"POST / HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\n",
            400,
        )

    def test_oversized_body_is_rejected_before_body_arrives(self) -> None:
        self.assert_protocol_status(
            b"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: 99\r\n\r\n",
            413,
        )

    def test_bare_newline_termination_is_rejected(self) -> None:
        self.assert_protocol_status(b"GET / HTTP/1.1\nHost: x\n\n", 400)


class HiddenNetworkContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = Server(
            ServiceConfig(
                worker_count=4,
                queue_size=8,
                max_connections=16,
                read_timeout=0.25,
            )
        )
        self.server.start()

    def tearDown(self) -> None:
        self.server.close()

    def test_pipelining_writes_two_complete_responses(self) -> None:
        raw = exchange(
            self.server.address,
            wire("GET", "/healthz", close=False) + wire("GET", "/healthz"),
        )
        self.assertEqual(2, raw.count(b"HTTP/1.1 200 OK"))
        self.assertTrue(raw.endswith(b'{"status":"ok"}'))

    def test_request_budget_stops_pipelined_dispatch(self) -> None:
        self.server.close()
        self.server = Server(
            ServiceConfig(
                worker_count=2,
                queue_size=2,
                max_connections=2,
                read_timeout=0.25,
                max_requests_per_connection=1,
            )
        )
        self.server.start()
        raw = exchange(
            self.server.address,
            wire("GET", "/healthz", close=False) + wire("GET", "/healthz"),
        )
        self.assertEqual(1, raw.count(b"HTTP/1.1 200 OK"))

    def test_compare_and_set_conflict_does_not_mutate(self) -> None:
        create = wire(
            "PUT",
            "/v1/counters/deploys",
            b'{"value":2}',
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(201, parse_one(exchange(self.server.address, create))[0])
        conflict = wire(
            "PUT",
            "/v1/counters/deploys",
            b'{"value":8}',
            headers={"Content-Type": "application/json", "If-Match": '"0"'},
        )
        self.assertEqual(409, parse_one(exchange(self.server.address, conflict))[0])
        _, _, body = parse_one(
            exchange(self.server.address, wire("GET", "/v1/counters/deploys"))
        )
        self.assertEqual(2, body["value"])

    def test_idempotency_key_conflict_cannot_cross_resources(self) -> None:
        first = wire(
            "POST",
            "/v1/counters/alpha/increment",
            b'{"delta":1}',
            headers={
                "Content-Type": "application/json",
                "Idempotency-Key": "shared-operation-key",
            },
        )
        self.assertEqual(200, parse_one(exchange(self.server.address, first))[0])
        conflict = wire(
            "POST",
            "/v1/counters/beta/increment",
            b'{"delta":1}',
            headers={
                "Content-Type": "application/json",
                "Idempotency-Key": "shared-operation-key",
            },
        )
        status, _, body = parse_one(exchange(self.server.address, conflict))
        self.assertEqual(409, status)
        self.assertIn("another operation", body["error"])
        self.assertEqual(
            404,
            parse_one(
                exchange(self.server.address, wire("GET", "/v1/counters/beta"))
            )[0],
        )

    def test_close_unblocks_idle_keepalive_before_read_timeout(self) -> None:
        self.server.close()
        self.server = Server(
            ServiceConfig(
                worker_count=2,
                queue_size=2,
                max_connections=2,
                read_timeout=3.0,
                shutdown_timeout=0.75,
            )
        )
        self.server.start()
        with socket.create_connection(self.server.address, timeout=2.0) as client:
            client.settimeout(2.0)
            client.sendall(wire("GET", "/healthz", close=False))
            self.assertTrue(read_one(client).startswith(b"HTTP/1.1 200 OK"))
            started = time.monotonic()
            self.server.close()
            elapsed = time.monotonic() - started
        self.assertLess(elapsed, 1.5)

    def test_concurrent_unique_increments_are_not_lost(self) -> None:
        failures: list[BaseException] = []

        def increment(worker: int) -> None:
            try:
                for step in range(15):
                    request = wire(
                        "POST",
                        "/v1/counters/parallel/increment",
                        b'{"delta":1}',
                        headers={
                            "Content-Type": "application/json",
                            "Idempotency-Key": f"{worker}-{step}",
                        },
                    )
                    if parse_one(exchange(self.server.address, request))[0] != 200:
                        raise AssertionError("increment failed")
            except BaseException as error:
                failures.append(error)

        threads = [threading.Thread(target=increment, args=(worker,)) for worker in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        if failures:
            raise failures[0]
        _, _, body = parse_one(
            exchange(self.server.address, wire("GET", "/v1/counters/parallel"))
        )
        self.assertEqual(90, body["value"])

    def test_malformed_protocol_gets_structured_error(self) -> None:
        status, headers, body = parse_one(
            exchange(self.server.address, b"GET / HTTP/1.1\r\n\r\n")
        )
        self.assertEqual(400, status)
        self.assertEqual("close", headers["connection"])
        self.assertIn("error", body)


if __name__ == "__main__":
    unittest.main()
