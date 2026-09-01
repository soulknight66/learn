from __future__ import annotations

import socket
import time

from http_service import Server, ServiceConfig


def main() -> int:
    config = ServiceConfig(worker_count=2, queue_size=2, read_timeout=0.12)
    with Server(config) as server:
        slow = [socket.create_connection(server.address, timeout=1.0) for _ in range(2)]
        try:
            for client in slow:
                client.sendall(b"GET /healthz HTTP/1.1\r\nHost: slow.local\r\nX-Padding: ")
            assert server.worker_thread_count <= max(config.worker_count, config.max_connections)
            time.sleep(0.3)
            request = b"GET /healthz HTTP/1.1\r\nHost: slow.local\r\nConnection: close\r\n\r\n"
            with socket.create_connection(server.address, timeout=1.0) as probe:
                probe.settimeout(1.0)
                probe.sendall(request)
                response = bytearray()
                while True:
                    chunk = probe.recv(65536)
                    if not chunk:
                        break
                    response.extend(chunk)
            assert bytes(response).startswith(b"HTTP/1.1 200 OK"), response
        finally:
            for client in slow:
                client.close()
    print("slow partial headers timed out and bounded capacity recovered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
