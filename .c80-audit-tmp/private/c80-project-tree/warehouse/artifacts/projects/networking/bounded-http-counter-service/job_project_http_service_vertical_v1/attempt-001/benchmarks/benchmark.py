from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import socket
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "sealed/shared"
IMPLEMENTATIONS = {
    "worker_pool": ROOT / "sealed/reference/http_service.py",
    "thread_per_connection": ROOT / "sealed/alternatives/thread_per_connection/http_service.py",
    "event_loop": ROOT / "sealed/alternatives/event_loop/http_service.py",
}


def load(name: str, path: Path) -> ModuleType:
    if str(SHARED) not in sys.path:
        sys.path.insert(0, str(SHARED))
    spec = importlib.util.spec_from_file_location(f"bench_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import implementation: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


REQUEST = b"GET /healthz HTTP/1.1\r\nHost: benchmark.local\r\nConnection: close\r\n\r\n"


def one_request(address: tuple[str, int]) -> int:
    started = time.perf_counter_ns()
    with socket.create_connection(address, timeout=2.0) as client:
        client.settimeout(2.0)
        client.sendall(REQUEST)
        response = bytearray()
        while True:
            chunk = client.recv(65536)
            if not chunk:
                break
            response.extend(chunk)
    if not bytes(response).startswith(b"HTTP/1.1 200 OK"):
        raise RuntimeError(f"benchmark received invalid response: {bytes(response[:100])!r}")
    return time.perf_counter_ns() - started


def measure(module: ModuleType, requests: int, concurrency: int) -> dict[str, object]:
    config = module.ServiceConfig(
        worker_count=max(2, concurrency),
        queue_size=max(4, concurrency * 2),
        max_connections=max(8, concurrency * 2),
        read_timeout=0.5,
    )
    server = module.Server(config)
    server.start()
    try:
        one_request(server.address)
        sequential_samples = [one_request(server.address) for _ in range(requests)]
        burst_started = time.perf_counter_ns()
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            burst_samples = list(
                executor.map(lambda _: one_request(server.address), range(requests))
            )
        burst_total = time.perf_counter_ns() - burst_started
    finally:
        server.close()
    return {
        "architecture": module.ARCHITECTURE,
        "sequential_latency_ns_raw": sequential_samples,
        "sequential_median_ns": statistics.median(sequential_samples),
        "sequential_p95_ns": sorted(sequential_samples)[max(0, int(len(sequential_samples) * 0.95) - 1)],
        "burst_latency_ns_raw": burst_samples,
        "burst_total_ns": burst_total,
        "burst_requests_per_second": requests / (burst_total / 1_000_000_000),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=40)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 5 <= args.requests <= 500:
        parser.error("requests must be between 5 and 500")
    if not 1 <= args.concurrency <= 32:
        parser.error("concurrency must be between 1 and 32")
    raw_results = {
        name: measure(load(name, path), args.requests, args.concurrency)
        for name, path in IMPLEMENTATIONS.items()
    }
    report = {
        "schema_version": 1,
        "hypothesis": (
            "A bounded worker pool should amortize thread creation, while the selector loop "
            "should stay competitive for tiny nonblocking handlers; this smoke workload is too "
            "small to establish production capacity."
        ),
        "parameters": {
            "requests_per_workload": args.requests,
            "concurrency": args.concurrency,
            "endpoint": "GET /healthz over a new loopback connection",
        },
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor() or "unreported",
            "cpu_count": os.cpu_count(),
            "timer": "time.perf_counter_ns",
            "network": "IPv4 loopback only",
        },
        "raw_results": raw_results,
        "interpretation_boundary": (
            "Measured values are machine-specific bounded smoke evidence, not a load-test, "
            "capacity promise, or claim of statistical significance."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        name: round(value["burst_requests_per_second"], 2)
        for name, value in raw_results.items()
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
