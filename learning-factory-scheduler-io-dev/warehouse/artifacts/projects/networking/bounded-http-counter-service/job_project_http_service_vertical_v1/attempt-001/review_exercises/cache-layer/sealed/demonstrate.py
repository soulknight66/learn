from __future__ import annotations

from cache_layer import ResponseCache
from http_core import Request, Response


class AccountApplication:
    def handle(self, request: Request) -> Response:
        identity = request.headers.get("authorization", "anonymous")
        return Response(200, {"content-type": "text/plain"}, f"profile:{identity}".encode())


def main() -> int:
    cached = ResponseCache(AccountApplication())
    alice = Request("GET", "/v1/me", "HTTP/1.1", {"authorization": "alice"}, b"")
    bob = Request("GET", "/v1/me", "HTTP/1.1", {"authorization": "bob"}, b"")
    alice_response = cached.handle(alice)
    bob_response = cached.handle(bob)
    assert alice_response.body == b"profile:alice"
    assert bob_response.body == b"profile:alice"
    assert bob_response.body != b"profile:bob"
    print("reproduced cross-principal response disclosure caused by the proposed cache key")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
