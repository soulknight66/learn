from __future__ import annotations

import socket

from http_service import CounterApp, Server, ServiceConfig


def exchange(address: tuple[str, int], target: str) -> bytes:
    request = (
        f"GET {target} HTTP/1.1\r\nHost: fault.local\r\nConnection: close\r\n\r\n"
    ).encode("ascii")
    with socket.create_connection(address, timeout=2.0) as client:
        client.settimeout(2.0)
        client.sendall(request)
        output = bytearray()
        while True:
            chunk = client.recv(65536)
            if not chunk:
                return bytes(output)
            output.extend(chunk)


def inject(request: object) -> None:
    if getattr(request, "target") == "/fault":
        raise RuntimeError("sensitive backend detail that must not escape")


def main() -> int:
    with Server(
        ServiceConfig(worker_count=2, read_timeout=0.2),
        CounterApp(fault_hook=inject),
    ) as server:
        failed = exchange(server.address, "/fault")
        assert failed.startswith(b"HTTP/1.1 500 Internal Server Error")
        assert b"sensitive backend detail" not in failed
        healthy = exchange(server.address, "/healthz")
        assert healthy.startswith(b"HTTP/1.1 200 OK")
        metrics = exchange(server.address, "/metrics")
        assert b"counter_service_application_errors_total 1" in metrics
    print("application fault was contained and the service remained healthy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
