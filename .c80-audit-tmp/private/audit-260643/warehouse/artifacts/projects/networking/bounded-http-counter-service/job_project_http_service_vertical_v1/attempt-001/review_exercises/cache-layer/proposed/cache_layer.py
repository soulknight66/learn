from __future__ import annotations

import threading

from http_core import Request, Response


class ResponseCache:
    """Proposed PR implementation; review before relying on it."""

    def __init__(self, application: object) -> None:
        self.application = application
        self.cache: dict[str, Response] = {}
        self.lock = threading.Lock()

    def handle(self, request: Request) -> Response:
        if request.method != "GET":
            return self.application.handle(request)
        with self.lock:
            if request.target in self.cache:
                return self.cache[request.target]
            response = self.application.handle(request)
            if response.status == 200:
                self.cache[request.target] = response
            return response
