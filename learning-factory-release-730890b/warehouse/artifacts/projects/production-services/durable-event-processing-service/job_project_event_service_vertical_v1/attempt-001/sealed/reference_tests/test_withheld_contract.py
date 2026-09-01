import json
import tempfile
import threading
import unittest
from pathlib import Path

from event_service import (
    BoundedDispatcher,
    EventService,
    InjectedCrash,
    JsonLogger,
    LeaseLost,
    Metrics,
)


class Clock:
    def __init__(self) -> None:
        self.value = 1_000.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class WithheldContractTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="event-service-hidden-")
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "queue.db"
        self.clock = Clock()
        self.service = EventService(
            self.path, clock=self.clock, max_attempts=3, base_backoff=1.0
        )

    def test_migration_is_restart_safe_and_versioned(self) -> None:
        EventService(self.path, clock=self.clock)
        with self.service._connect() as connection:
            versions = connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            ).fetchall()
            message_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(messages)")
            }
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        self.assertEqual(["001_initial.sql"], [row[0] for row in versions])
        self.assertTrue({"messages", "effects", "dead_letters"} <= tables)
        self.assertIn("lease_token", message_columns)

    def test_concurrent_claim_has_one_winner(self) -> None:
        self.service.ingest("only-once", {})
        barrier = threading.Barrier(6)
        winners = []
        failures = []
        lock = threading.Lock()

        def compete(index: int) -> None:
            try:
                barrier.wait(timeout=5)
                delivery = self.service.claim(f"worker-{index}")
                if delivery is not None:
                    with lock:
                        winners.append(delivery)
            except BaseException as error:
                with lock:
                    failures.append(error)

        threads = [threading.Thread(target=compete, args=(index,)) for index in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual([], failures)
        self.assertEqual(1, len(winners))

    def test_expired_lease_recovers_after_process_crash(self) -> None:
        self.service.ingest("recover", {})
        abandoned = self.service.claim("dead-worker", lease_seconds=3)
        assert abandoned is not None
        self.assertIsNone(self.service.claim("healthy-worker"))
        self.clock.advance(3)
        recovered = self.service.claim("healthy-worker")
        assert recovered is not None
        self.assertEqual(abandoned.message_id, recovered.message_id)
        self.assertEqual(2, recovered.attempt)
        with self.assertRaises(LeaseLost):
            self.service.acknowledge(abandoned)

    def test_stale_same_owner_delivery_is_fenced_from_new_claim(self) -> None:
        self.service.ingest("fenced", {})
        stale = self.service.claim("stable-worker", lease_seconds=1)
        assert stale is not None
        self.clock.advance(1)
        current = self.service.claim("stable-worker", lease_seconds=10)
        assert current is not None
        self.assertNotEqual(stale.lease_token, current.lease_token)
        for operation in (
            lambda: self.service.heartbeat(stale),
            lambda: self.service.acknowledge(stale),
            lambda: self.service.fail(stale, "stale failure"),
            lambda: self.service.release(stale),
        ):
            with self.assertRaises(LeaseLost):
                operation()
        self.assertTrue(self.service.deliver(current, {"winner": True}))

    def test_expired_release_is_rejected(self) -> None:
        self.service.ingest("expired-release", {})
        delivery = self.service.claim("worker", lease_seconds=1)
        assert delivery is not None
        self.clock.advance(1)
        with self.assertRaises(LeaseLost):
            self.service.release(delivery)

    def test_heartbeat_never_shortens_a_live_lease(self) -> None:
        self.service.ingest("heartbeat", {})
        delivery = self.service.claim("worker", lease_seconds=20)
        assert delivery is not None
        self.clock.advance(1)
        refreshed = self.service.heartbeat(delivery, lease_seconds=1)
        self.assertEqual(delivery.lease_expires_at, refreshed.lease_expires_at)

    def test_repeated_crash_expiry_exhausts_attempt_budget(self) -> None:
        service = EventService(
            self.path, clock=self.clock, max_attempts=2, base_backoff=1.0
        )
        service.ingest("crash-loop", {})
        first = service.claim("worker-1", lease_seconds=1)
        assert first is not None
        self.clock.advance(1)
        second = service.claim("worker-2", lease_seconds=1)
        assert second is not None
        self.assertEqual(2, second.attempt)
        self.clock.advance(1)
        self.assertIsNone(service.claim("worker-3", lease_seconds=1))
        self.assertEqual(1, service.counts()["DEAD"])
        dead = service.list_dead_letters()["items"]
        self.assertEqual(2, dead[0]["attempts"])
        self.assertIn("lease expired", dead[0]["reason"])

    def test_crash_after_side_effect_before_ack_does_not_duplicate_effect(self) -> None:
        self.service.ingest("payment-7", {"cents": 500})
        first = self.service.claim("worker-a", lease_seconds=2)
        assert first is not None
        with self.assertRaises(InjectedCrash):
            self.service.deliver(
                first,
                {"charged": 500},
                fault="after_side_effect_before_ack",
            )
        self.assertEqual(1, self.service.effect_count())
        self.assertEqual(1, self.service.counts()["CLAIMED"])
        self.clock.advance(2)
        replay = self.service.claim("worker-b", lease_seconds=2)
        assert replay is not None
        self.assertFalse(self.service.deliver(replay, {"charged": 500}))
        self.assertEqual(1, self.service.effect_count())
        self.assertEqual(1, self.service.counts()["DONE"])

    def test_retry_schedule_and_poison_dead_letter_boundary(self) -> None:
        self.service.ingest("poison", {})
        first = self.service.claim("w")
        assert first is not None
        self.assertEqual("RETRY_WAIT", self.service.fail(first, "one"))
        self.clock.advance(1)
        second = self.service.claim("w")
        assert second is not None
        self.assertEqual("RETRY_WAIT", self.service.fail(second, "two"))
        self.clock.advance(1.99)
        self.assertIsNone(self.service.claim("w"))
        self.clock.advance(0.01)
        third = self.service.claim("w")
        assert third is not None
        self.assertEqual("DEAD", self.service.fail(third, "permanent"))
        page = self.service.list_dead_letters()
        self.assertEqual(1, len(page["items"]))
        self.assertEqual(3, page["items"][0]["attempts"])
        self.service.requeue_dead_letter(third.message_id)
        self.assertEqual(1, self.service.counts()["READY"])
        self.assertEqual([], self.service.list_dead_letters()["items"])

    def test_requeue_preserves_prior_dead_letter_audit_cycle(self) -> None:
        service = EventService(self.path, clock=self.clock, max_attempts=1)
        message_id, _ = service.ingest("repeat-poison", {})
        first = service.claim("worker")
        assert first is not None
        self.assertEqual("DEAD", service.fail(first, "cycle one"))
        service.requeue_dead_letter(message_id)
        second = service.claim("worker")
        assert second is not None
        self.assertEqual("DEAD", service.fail(second, "cycle two"))
        with service._connect() as connection:
            history = connection.execute(
                """
                SELECT reason,requeued_at FROM dead_letters
                WHERE message_id=? ORDER BY dead_letter_id
                """,
                (message_id,),
            ).fetchall()
        self.assertEqual(["cycle one", "cycle two"], [row["reason"] for row in history])
        self.assertIsNotNone(history[0]["requeued_at"])
        self.assertIsNone(history[1]["requeued_at"])

    def test_keyset_pagination_never_skips_or_repeats(self) -> None:
        for index in range(7):
            self.service.ingest(f"page-{index}", {"index": index})
        seen = []
        after = 0
        while True:
            page = self.service.list_messages(limit=3, after=after)
            seen.extend(item["message_id"] for item in page["items"])
            if page["next_after"] is None:
                break
            after = page["next_after"]
        self.assertEqual(sorted(seen), seen)
        self.assertEqual(7, len(set(seen)))

    def test_bounded_prefetch_structured_observability_and_graceful_drain(self) -> None:
        for index in range(3):
            self.service.ingest(f"bounded-{index}", {"index": index})
        records = []
        metrics = Metrics()
        dispatcher = BoundedDispatcher(
            self.service,
            "bounded-worker",
            capacity=2,
            logger=JsonLogger(records.append, self.clock),
            metrics=metrics,
        )
        self.assertEqual(1, dispatcher.fill())
        self.assertEqual(1, dispatcher.buffered)
        self.assertEqual(0, dispatcher.fill())
        dispatcher.request_stop()
        self.assertEqual(0, dispatcher.fill())
        self.assertEqual(1, dispatcher.run_until_idle(lambda delivery: {"ok": True}))
        self.assertEqual(0, dispatcher.buffered)
        self.assertEqual(1, self.service.counts()["DONE"])
        self.assertEqual(2, self.service.counts()["READY"])
        self.assertEqual(1, metrics.snapshot()["delivered_total"])
        decoded = [json.loads(line) for line in records]
        self.assertTrue(all({"ts", "level", "event"} <= set(row) for row in decoded))
        self.assertIn("shutdown_requested", {row["event"] for row in decoded})

    def test_claim_on_demand_survives_slow_sequential_handlers(self) -> None:
        for index in range(3):
            self.service.ingest(f"slow-{index}", {})
        dispatcher = BoundedDispatcher(
            self.service,
            "slow-worker",
            capacity=8,
            lease_seconds=1,
            logger=JsonLogger(lambda line: None, self.clock),
        )

        def handler(delivery):
            self.clock.advance(0.6)
            return {"attempt": delivery.attempt}

        self.assertEqual(3, dispatcher.run_until_idle(handler))
        self.assertEqual(3, self.service.counts()["DONE"])

    def test_logging_sink_failure_cannot_reclassify_committed_delivery(self) -> None:
        self.service.ingest("logging-failure", {})

        def broken_sink(line: str) -> None:
            raise OSError("closed log sink")

        metrics = Metrics()
        dispatcher = BoundedDispatcher(
            self.service,
            "worker",
            logger=JsonLogger(broken_sink, self.clock),
            metrics=metrics,
        )
        self.assertEqual(1, dispatcher.run_until_idle(lambda delivery: {"ok": True}))
        self.assertEqual(1, self.service.counts()["DONE"])
        self.assertEqual(1, metrics.snapshot()["logging_errors_total"])


if __name__ == "__main__":
    unittest.main()
