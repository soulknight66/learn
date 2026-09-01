from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

from event_service import BoundedDispatcher, EventService, JsonLogger


def sample(messages: int, capacity: int, repetition: int) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="event-benchmark-") as temporary:
        path = Path(temporary) / "queue.db"
        service = EventService(path)
        started = time.perf_counter_ns()
        for index in range(messages):
            service.ingest(
                f"bench-{repetition}-{capacity}-{index}",
                {"index": index, "payload": "x" * 48},
            )
        ingested = time.perf_counter_ns()
        dispatcher = BoundedDispatcher(
            service,
            f"bench-worker-{capacity}",
            capacity=capacity,
            logger=JsonLogger(lambda line: None),
        )
        processed = dispatcher.run_until_idle(lambda delivery: {"ok": True})
        finished = time.perf_counter_ns()
        if processed != messages or service.counts()["DONE"] != messages:
            raise RuntimeError("benchmark workload did not complete")
        total_ns = finished - started
        return {
            "capacity": capacity,
            "effective_outstanding_limit": 1,
            "repetition": repetition,
            "messages": messages,
            "ingest_ns": ingested - started,
            "delivery_ns": finished - ingested,
            "total_ns": total_ns,
            "messages_per_second": messages / (total_ns / 1_000_000_000),
            "database_bytes": path.stat().st_size,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--messages", type=int, default=80)
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if not 1 <= args.messages <= 2_000 or not 1 <= args.repetitions <= 10:
        raise SystemExit("benchmark bounds exceeded")
    raw_samples = [
        sample(args.messages, capacity, repetition)
        for capacity in (1, 8)
        for repetition in range(args.repetitions)
    ]
    implementation = Path(__import__("event_service").__file__).resolve()
    document = {
        "schema_version": 1,
        "measured_at_unix_ns": time.time_ns(),
        "hypothesis": (
            "The claim-on-demand reference keeps one outstanding lease, so changing the "
            "configured future capacity should not create a prefetch throughput benefit. "
            "Observed differences are descriptive measurement noise."
        ),
        "parameters": {
            "messages": args.messages,
            "repetitions": args.repetitions,
            "capacities": [1, 8],
            "dispatch_policy": "claim_on_demand_one_outstanding",
            "payload_bytes_approximate": 75,
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "sqlite": sqlite3.sqlite_version,
            "implementation": str(implementation),
            "implementation_sha256": hashlib.sha256(
                implementation.read_bytes()
            ).hexdigest(),
            "timer": "time.perf_counter_ns",
        },
        "command": list(sys.argv),
        "raw_samples": raw_samples,
        "summary": {
            str(capacity): {
                "minimum_messages_per_second": min(
                    float(row["messages_per_second"])
                    for row in raw_samples
                    if row["capacity"] == capacity
                ),
                "maximum_messages_per_second": max(
                    float(row["messages_per_second"])
                    for row in raw_samples
                    if row["capacity"] == capacity
                ),
            }
            for capacity in (1, 8)
        },
        "interpretation_boundary": (
            "Bounded local smoke data, not a capacity plan: no remote broker, multi-process "
            "contention, fsync audit, long soak, confidence interval, or production hardware. "
            "Capacity is intentionally inert until a lease-keeper-backed prefetcher exists."
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = output.with_name(output.name + ".tmp")
    temporary_output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary_output.replace(output)
    print(json.dumps({"samples": len(raw_samples), "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
