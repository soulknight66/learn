import os
import subprocess
import sys
import tempfile
from pathlib import Path

from event_service import EventService


class Clock:
    def __init__(self) -> None:
        self.now = 10.0

    def __call__(self) -> float:
        return self.now


def child(path: Path) -> None:
    clock = Clock()
    service = EventService(path, clock=clock)
    delivery = service.claim("crashing-worker", lease_seconds=1)
    assert delivery is not None
    service.apply_effect(delivery, {"charged": 700})
    # Deliberately skip normal unwinding and acknowledgement. The effect's
    # connection has committed and closed, so this is the lost-ack boundary.
    os._exit(71)


if len(sys.argv) == 3 and sys.argv[1] == "--child":
    child(Path(sys.argv[2]))

with tempfile.TemporaryDirectory(prefix="event-fault-") as temporary:
    path = Path(temporary) / "queue.db"
    clock = Clock()
    service = EventService(path, clock=clock)
    service.ingest("charge-1", {"cents": 700})
    crashed = subprocess.run(
        [sys.executable, __file__, "--child", str(path)], check=False
    )
    if crashed.returncode != 71:
        raise SystemExit(f"child exited {crashed.returncode}, expected 71")
    if service.effect_count() != 1 or service.counts()["CLAIMED"] != 1:
        raise SystemExit("crash boundary was not durable")
    clock.now += 1
    replay = service.claim("replacement-worker", lease_seconds=1)
    assert replay is not None
    if service.deliver(replay, {"charged": 700}) is not False:
        raise SystemExit("replay repeated an idempotent side effect")
    if service.effect_count() != 1 or service.counts()["DONE"] != 1:
        raise SystemExit("recovery did not acknowledge exactly one effect")
    print("observed child-process death after durable effect, lost ack, lease recovery, and duplicate suppression")
