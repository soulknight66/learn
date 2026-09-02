#!/usr/bin/env python3
"""Strictly validate and execute every declared adversarial vector."""

from __future__ import annotations

import argparse
import json
import os
import selectors
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, NamedTuple

U32_MAX = (1 << 32) - 1
FLAG_BITS = {"READ": 1, "WRITE": 2, "EXEC": 4}
CAPTURE_LIMIT = 65536
READ_CHUNK = 8192

EXPECTED: dict[str, dict[str, Any]] = {
    "pid_terminal_value": {
        "spawn_results": [U32_MAX, 0], "invariant": True,
    },
    "pid_stale_reuse": {
        "old_pid_absent": True, "replacement_pid": 2, "slot_reused": True,
    },
    "scheduler_duplicate_pid": {
        "invariant": False, "operation_result": 0, "mutation": "none",
    },
    "scheduler_current_mismatch": {
        "invariant": False, "operation_result": 0, "mutation": "none",
    },
    "frame_exact_top": {"accepted": True, "first_frame": 4294963200},
    "frame_past_top": {"accepted": False, "mutation": "none"},
    "permission_subset": {"translated": False, "output": "unchanged"},
    "vm_final_physical_byte": {
        "translated": True, "physical_address": U32_MAX,
    },
    "ramfs_addition_wrap": {"result": "LF_ERR_RANGE", "mutation": "none"},
    "ramfs_full_capacity_create": {
        "result": "LF_ERR_NO_SPACE", "mutation": "none",
    },
    "null_zero_read": {"result": 0},
    "ramfs_scrub_reuse": {
        "cleared_before_reuse": True, "replacement_data_zero": True,
    },
}


class VectorError(ValueError):
    pass


class RunResult(NamedTuple):
    returncode: int
    stdout: str
    stderr: str


def _append_bounded(buffer: bytearray, chunk: bytes, limit: int) -> bool:
    remaining = max(0, limit - len(buffer))
    buffer.extend(chunk[:remaining])
    return len(chunk) > remaining


def _decode_capture(buffer: bytearray, truncated: bool) -> str:
    result = bytes(buffer).decode("utf-8", errors="replace")
    if truncated:
        result += "\n[output capture truncated]\n"
    return result


def _kill_process_group(process_group: int) -> None:
    try:
        os.killpg(process_group, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _read_ready(
    selector: selectors.BaseSelector,
    buffers: dict[str, bytearray],
    truncated: dict[str, bool],
    capture_limit: int,
    timeout: float,
) -> None:
    for key, _ in selector.select(timeout):
        try:
            chunk = os.read(key.fd, READ_CHUNK)
        except BlockingIOError:
            continue
        if chunk:
            stream = str(key.data)
            truncated[stream] |= _append_bounded(
                buffers[stream], chunk, capture_limit
            )
        else:
            selector.unregister(key.fileobj)
            key.fileobj.close()


def run_bounded(
    command: list[str],
    *,
    timeout_seconds: float = 5.0,
    capture_limit: int = CAPTURE_LIMIT,
) -> RunResult:
    """Run one argv command in a new session with bounded capture and cleanup."""
    if not command:
        raise ValueError("command must not be empty")
    if timeout_seconds <= 0.0:
        raise ValueError("timeout_seconds must be positive")
    if capture_limit < 0:
        raise ValueError("capture_limit must be nonnegative")

    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        close_fds=True,
    )
    assert process.stdout is not None
    assert process.stderr is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    truncated = {"stdout": False, "stderr": False}
    deadline = time.monotonic() + timeout_seconds
    timed_out = False

    try:
        while process.poll() is None or selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0.0:
                timed_out = True
                _kill_process_group(process.pid)
                try:
                    process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1.0)
                drain_deadline = time.monotonic() + 1.0
                while selector.get_map() and time.monotonic() < drain_deadline:
                    _read_ready(
                        selector,
                        buffers,
                        truncated,
                        capture_limit,
                        0.05,
                    )
                break
            _read_ready(
                selector,
                buffers,
                truncated,
                capture_limit,
                min(0.05, remaining),
            )

        if not timed_out:
            process.wait()
            # A direct child can exit after leaving descendants behind. They
            # remain in this dedicated process group and are never allowed to
            # escape the runner, even if they closed the capture descriptors.
            _kill_process_group(process.pid)
    finally:
        for key in list(selector.get_map().values()):
            selector.unregister(key.fileobj)
            key.fileobj.close()
        selector.close()

    stdout = _decode_capture(buffers["stdout"], truncated["stdout"])
    stderr = _decode_capture(buffers["stderr"], truncated["stderr"])
    if timed_out:
        raise subprocess.TimeoutExpired(
            command, timeout_seconds, output=stdout, stderr=stderr
        )
    assert process.returncode is not None
    return RunResult(process.returncode, stdout, stderr)


def exact_keys(value: Any, keys: set[str], location: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise VectorError(f"{location}: expected exactly {sorted(keys)}")
    return value


def u32(value: Any, location: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= U32_MAX:
        raise VectorError(f"{location}: expected an unsigned 32-bit integer")
    return value


def flags(value: Any, location: str) -> int:
    if not isinstance(value, list) or not value:
        raise VectorError(f"{location}: expected a nonempty list of unique flags")
    try:
        if len(set(value)) != len(value):
            raise VectorError(
                f"{location}: expected a nonempty list of unique flags"
            )
        return sum(FLAG_BITS[item] for item in value)
    except (KeyError, TypeError) as error:
        raise VectorError(f"{location}: unknown flag") from error


def input_arguments(case: str, raw: Any) -> list[str]:
    if case == "pid_terminal_value":
        data = exact_keys(raw, {"next_pid"}, case)
        values = [u32(data["next_pid"], f"{case}.next_pid")]
    elif case == "pid_stale_reuse":
        data = exact_keys(raw, {"initial_next_pid"}, case)
        values = [u32(data["initial_next_pid"], f"{case}.initial_next_pid")]
    elif case == "scheduler_duplicate_pid":
        data = exact_keys(raw, {"first_slot", "duplicate_slot"}, case)
        values = [u32(data[name], f"{case}.{name}") for name in
                  ("first_slot", "duplicate_slot")]
    elif case == "scheduler_current_mismatch":
        data = exact_keys(raw, {"running_slot", "current_slot"}, case)
        values = [u32(data[name], f"{case}.{name}") for name in
                  ("running_slot", "current_slot")]
    elif case in {"frame_exact_top", "frame_past_top"}:
        data = exact_keys(raw, {"base", "count"}, case)
        values = [u32(data[name], f"{case}.{name}") for name in ("base", "count")]
    elif case == "permission_subset":
        data = exact_keys(raw, {"mapped", "requested"}, case)
        values = [flags(data["mapped"], f"{case}.mapped"),
                  flags(data["requested"], f"{case}.requested")]
    elif case == "vm_final_physical_byte":
        data = exact_keys(
            raw,
            {"virtual_base", "virtual_address", "physical_base", "requested"},
            case,
        )
        values = [u32(data[name], f"{case}.{name}") for name in
                  ("virtual_base", "virtual_address", "physical_base")]
        values.append(flags(data["requested"], f"{case}.requested"))
    elif case == "ramfs_addition_wrap":
        data = exact_keys(raw, {"offset", "length"}, case)
        values = [u32(data[name], f"{case}.{name}") for name in ("offset", "length")]
    elif case == "ramfs_full_capacity_create":
        data = exact_keys(raw, {"capacity"}, case)
        values = [u32(data["capacity"], f"{case}.capacity")]
    elif case == "null_zero_read":
        data = exact_keys(raw, {"buffer", "length"}, case)
        if data["buffer"] is not None:
            raise VectorError(f"{case}.buffer: expected null")
        values = [u32(data["length"], f"{case}.length")]
    elif case == "ramfs_scrub_reuse":
        data = exact_keys(raw, {"payload_byte", "length"}, case)
        values = [u32(data[name], f"{case}.{name}") for name in
                  ("payload_byte", "length")]
    else:
        raise VectorError(f"unsupported case: {case}")
    return [str(value) for value in values]


def load_vectors(path: Path) -> list[tuple[str, list[str]]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise VectorError(f"cannot load {path}: {error}") from error
    root = exact_keys(
        document,
        {"schema_version", "provenance", "validation_label", "vectors"},
        "root",
    )
    if root["schema_version"] != 1:
        raise VectorError("root.schema_version: expected 1")
    if root["validation_label"] != "UNVALIDATED_ADVERSARIAL_VECTORS":
        raise VectorError("root.validation_label: unexpected value")
    if not isinstance(root["provenance"], str) or not root["provenance"]:
        raise VectorError("root.provenance: expected a nonempty string")
    if not isinstance(root["vectors"], list):
        raise VectorError("root.vectors: expected a list")

    result: list[tuple[str, list[str]]] = []
    seen: set[str] = set()
    for index, raw_vector in enumerate(root["vectors"]):
        vector = exact_keys(raw_vector, {"case", "input", "expect"}, f"vectors[{index}]")
        case = vector["case"]
        if not isinstance(case, str) or case not in EXPECTED:
            raise VectorError(f"vectors[{index}].case: unsupported case")
        if case in seen:
            raise VectorError(f"vectors[{index}].case: duplicate {case}")
        if vector["expect"] != EXPECTED[case]:
            raise VectorError(f"vectors[{index}].expect: contract mismatch for {case}")
        result.append((case, input_arguments(case, vector["input"])))
        seen.add(case)
    missing = set(EXPECTED) - seen
    if missing:
        raise VectorError(f"root.vectors: missing cases {sorted(missing)}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", required=True, type=Path)
    parser.add_argument("--runner", required=True, type=Path)
    args = parser.parse_args()
    try:
        vectors = load_vectors(args.vectors)
        for case, case_args in vectors:
            command = [str(args.runner), case, *case_args]
            try:
                completed = run_bounded(command, timeout_seconds=5.0)
            except subprocess.TimeoutExpired as error:
                if error.output:
                    sys.stderr.write(str(error.output))
                if error.stderr:
                    sys.stderr.write(str(error.stderr))
                raise VectorError(f"{case}: runner exceeded 5 seconds") from error
            if completed.returncode != 0:
                sys.stderr.write(completed.stdout)
                sys.stderr.write(completed.stderr)
                raise VectorError(f"{case}: runner exited {completed.returncode}")
    except (OSError, VectorError) as error:
        print(f"adversarial_vectors: FAIL: {error}", file=sys.stderr)
        return 1
    print(f"adversarial_vectors: PASS ({len(vectors)} vectors)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
