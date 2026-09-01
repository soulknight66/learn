import argparse
import random
import sqlite3
import tempfile
from pathlib import Path

from event_service import EventService


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def check_invariants(service: EventService, expected_keys: set[str]) -> None:
    with service._connect() as connection:
        rows = connection.execute("SELECT * FROM messages ORDER BY message_id").fetchall()
        effects = connection.execute("SELECT message_id FROM effects").fetchall()
        dead = connection.execute(
            "SELECT message_id FROM dead_letters WHERE requeued_at IS NULL"
        ).fetchall()
    if {row["idempotency_key"] for row in rows} != expected_keys:
        raise AssertionError("queue diverged from unique-key model")
    if len({row["message_id"] for row in effects}) != len(effects):
        raise AssertionError("duplicate durable effects")
    for row in rows:
        owned = row["lease_owner"] is not None and row["lease_expires_at"] is not None
        if owned != (row["state"] == "CLAIMED"):
            raise AssertionError("lease columns disagree with state")
    dead_ids = {row["message_id"] for row in dead}
    if dead_ids != {row["message_id"] for row in rows if row["state"] == "DEAD"}:
        raise AssertionError("dead-letter projection diverged")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260830)
    parser.add_argument("--steps", type=int, default=160)
    args = parser.parse_args()
    randomizer = random.Random(args.seed)
    clock = Clock()
    with tempfile.TemporaryDirectory(prefix="event-model-") as temporary:
        service = EventService(
            Path(temporary) / "queue.db",
            clock=clock,
            max_attempts=3,
            base_backoff=0.25,
        )
        expected_keys = set()
        for step in range(args.steps):
            if randomizer.random() < 0.55:
                key = f"key-{randomizer.randrange(35)}"
                payload = {"key": key}
                service.ingest(key, payload)
                expected_keys.add(key)
            else:
                delivery = service.claim(f"worker-{step % 4}", lease_seconds=1)
                if delivery is not None:
                    if randomizer.random() < 0.72:
                        service.deliver(delivery, {"ok": True})
                    else:
                        service.fail(delivery, "modeled transient")
            clock.now += randomizer.choice((0.0, 0.25, 0.5, 1.0))
            check_invariants(service, expected_keys)
        # Advance past every retry and drain to a stable DONE/DEAD state.
        for step in range(500):
            clock.now += 2
            delivery = service.claim(f"drain-{step % 3}", lease_seconds=1)
            if delivery is None:
                if service.counts()["RETRY_WAIT"] == 0:
                    break
                continue
            service.deliver(delivery, {"ok": True})
        check_invariants(service, expected_keys)
        counts = service.counts()
        if counts["READY"] or counts["CLAIMED"] or counts["RETRY_WAIT"]:
            raise AssertionError(f"model did not quiesce: {counts}")
        print(f"seed={args.seed} steps={args.steps} keys={len(expected_keys)} counts={counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
