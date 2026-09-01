import tempfile
import threading
from pathlib import Path

from event_service import EventService


with tempfile.TemporaryDirectory(prefix="event-stress-") as temporary:
    service = EventService(Path(temporary) / "queue.db")
    barrier = threading.Barrier(6)
    errors = []
    lock = threading.Lock()

    def producer(worker: int) -> None:
        try:
            barrier.wait(timeout=5)
            for index in range(30):
                service.ingest(f"item-{index}", {"index": index})
        except BaseException as error:
            with lock:
                errors.append(error)

    threads = [threading.Thread(target=producer, args=(index,)) for index in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)
    if errors or any(thread.is_alive() for thread in threads):
        raise SystemExit(f"producer stress failed: {errors!r}")
    if sum(service.counts().values()) != 30:
        raise SystemExit("idempotent concurrent ingest created duplicates")

    delivered = []
    errors.clear()

    def consumer(worker: int) -> None:
        try:
            while True:
                delivery = service.claim(f"consumer-{worker}", lease_seconds=10)
                if delivery is None:
                    return
                service.deliver(delivery, {"worker": worker})
                with lock:
                    delivered.append(delivery.message_id)
        except BaseException as error:
            with lock:
                errors.append(error)

    consumers = [threading.Thread(target=consumer, args=(index,)) for index in range(4)]
    for thread in consumers:
        thread.start()
    for thread in consumers:
        thread.join(timeout=15)
    if errors or any(thread.is_alive() for thread in consumers):
        raise SystemExit(f"consumer stress failed: {errors!r}")
    if len(delivered) != 30 or len(set(delivered)) != 30:
        raise SystemExit("a message was duplicated or lost")
    if service.effect_count() != 30 or service.counts()["DONE"] != 30:
        raise SystemExit("terminal state disagrees with durable effects")
    print("concurrent idempotent ingest and atomic claims passed")
