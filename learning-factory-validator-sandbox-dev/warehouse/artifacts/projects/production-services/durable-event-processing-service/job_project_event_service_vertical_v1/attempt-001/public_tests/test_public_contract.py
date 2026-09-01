import tempfile
import unittest
from pathlib import Path

from event_service import EventService


class Clock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class PublicContractTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="event-service-public-")
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "events.db"
        self.clock = Clock()
        self.service = EventService(
            self.path, clock=self.clock, max_attempts=3, base_backoff=2.0
        )

    def test_ingest_is_idempotent_and_rejects_key_reuse(self) -> None:
        first, created = self.service.ingest("order-17", {"amount": 3})
        second, duplicate_created = self.service.ingest("order-17", {"amount": 3})
        self.assertEqual(first, second)
        self.assertTrue(created)
        self.assertFalse(duplicate_created)
        with self.assertRaises(ValueError):
            self.service.ingest("order-17", {"amount": 99})

    def test_claim_then_ack_is_durable(self) -> None:
        self.service.ingest("a", {"kind": "email"})
        delivery = self.service.claim("worker-a", lease_seconds=5)
        self.assertIsNotNone(delivery)
        assert delivery is not None
        self.assertEqual(1, delivery.attempt)
        self.assertTrue(self.service.deliver(delivery, {"sent": True}))
        self.assertEqual(1, self.service.counts()["DONE"])
        self.assertEqual(1, self.service.effect_count())

    def test_failure_waits_for_exponential_retry(self) -> None:
        self.service.ingest("retry-me", {})
        first = self.service.claim("worker-a")
        assert first is not None
        self.assertEqual("RETRY_WAIT", self.service.fail(first, "temporary"))
        self.assertIsNone(self.service.claim("worker-b"))
        self.clock.advance(2.0)
        second = self.service.claim("worker-b")
        self.assertIsNotNone(second)
        assert second is not None
        self.assertEqual(2, second.attempt)


if __name__ == "__main__":
    unittest.main()
