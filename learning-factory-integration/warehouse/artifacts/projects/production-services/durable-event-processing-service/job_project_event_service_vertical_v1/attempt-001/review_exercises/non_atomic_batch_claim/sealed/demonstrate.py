import tempfile
import threading
from pathlib import Path

from event_service import EventService
from unsafe_claim import claim_without_transaction


with tempfile.TemporaryDirectory(prefix="event-review-") as temporary:
    path = Path(temporary) / "queue.db"
    service = EventService(path)
    expected, _ = service.ingest("review-target", {})
    selected = threading.Barrier(2)
    results = []
    lock = threading.Lock()

    def run(owner: str) -> None:
        value = claim_without_transaction(str(path), owner, selected)
        with lock:
            results.append(value)

    threads = [threading.Thread(target=run, args=(f"review-{index}",)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    if any(thread.is_alive() for thread in threads):
        raise SystemExit("review reproducer stalled")
    if results != [expected, expected] and sorted(results) != [expected, expected]:
        raise SystemExit(f"expected duplicate ownership, observed {results!r}")
    print("demonstrated two callers returning ownership of one message")
