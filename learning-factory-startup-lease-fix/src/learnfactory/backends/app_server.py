from __future__ import annotations

import shutil


class AppServerBackend:
    """Capability marker for the installed experimental interface.

    It intentionally cannot execute jobs until a pinned protocol schema and compatibility tests are
    checked in. Selecting an experimental control surface silently would weaken restart guarantees.
    """

    name = "app-server"

    @staticmethod
    def available() -> bool:
        return shutil.which("codex") is not None

    def start_job(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError("app-server backend is experimental and not enabled; use exec")
