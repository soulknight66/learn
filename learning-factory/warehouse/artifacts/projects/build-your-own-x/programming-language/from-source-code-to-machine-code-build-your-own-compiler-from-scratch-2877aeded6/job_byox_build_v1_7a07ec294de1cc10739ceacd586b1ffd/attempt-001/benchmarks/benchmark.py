"""Small deterministic Minnow compile/execute timing harness."""

import argparse
import io
import json
import statistics
import time

from minnow import compile_source, run_bytecode


def source_for(loop_count):
    return f"""
        let n = {loop_count};
        let total = 0;
        while (n > 0) {{
            total = total + n;
            n = n - 1;
        }}
        print total;
    """


def measure(iterations, loop_count):
    source = source_for(loop_count)
    warm_binary = compile_source(source)
    run_bytecode(warm_binary, io.StringIO(), step_limit=loop_count * 20 + 100)
    compile_samples = []
    run_samples = []
    bytecode_size = 0
    for _ in range(iterations):
        started = time.perf_counter_ns()
        binary = compile_source(source)
        compile_samples.append(time.perf_counter_ns() - started)
        bytecode_size = len(binary)
        output = io.StringIO()
        started = time.perf_counter_ns()
        run_bytecode(binary, output, step_limit=loop_count * 20 + 100)
        run_samples.append(time.perf_counter_ns() - started)
        expected = loop_count * (loop_count + 1) // 2
        if output.getvalue() != f"{expected}\n":
            raise RuntimeError("benchmark program produced an unexpected result")
    return {
        "bytecode_bytes": bytecode_size,
        "compile_median_ns": int(statistics.median(compile_samples)),
        "iterations": iterations,
        "loop_count": loop_count,
        "run_median_ns": int(statistics.median(run_samples)),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=7)
    parser.add_argument("--loop-count", type=int, default=1000)
    arguments = parser.parse_args()
    if arguments.iterations <= 0 or arguments.loop_count <= 0:
        parser.error("values must be positive")
    print(json.dumps(measure(arguments.iterations, arguments.loop_count), sort_keys=True))


if __name__ == "__main__":
    main()
