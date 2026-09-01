import tempfile
from pathlib import Path

from event_service import EventService


class Clock:
    def __init__(self) -> None:
        self.now = 50.0

    def __call__(self) -> float:
        return self.now


with tempfile.TemporaryDirectory(prefix="event-poison-regression-") as temporary:
    clock = Clock()
    service = EventService(
        Path(temporary) / "queue.db",
        clock=clock,
        max_attempts=2,
        base_backoff=1,
    )
    service.ingest("poison", {})
    first = service.claim("worker")
    assert first is not None
    if service.fail(first, "still bad") != "RETRY_WAIT":
        raise SystemExit("first failure should be retryable")
    clock.now += 1
    second = service.claim("worker")
    assert second is not None
    state = service.fail(second, "still bad")
    if state != "DEAD":
        print(f"BUG REPRODUCED: max-attempt message remained {state}")
        # A distinct exit code prevents an unrelated Python crash (normally 1)
        # from masquerading as proof that this exact bug reproduced.
        raise SystemExit(23)
    if service.counts()["DEAD"] != 1 or len(service.list_dead_letters()["items"]) != 1:
        raise SystemExit("dead-letter projection missing")
    print("message moved to dead letter on the configured final attempt")
