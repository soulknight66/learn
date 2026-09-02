"""Manual benchmark harness; not part of validation and no numbers are pre-recorded."""

from statistics import median
from time import perf_counter_ns

from pebble import Interpreter, read_one


PROGRAM = read_one("(+ (* 7 8) (/ 99 3) (- 20 4 1))")
SAMPLES = 7
ITERATIONS = 10_000


def main() -> None:
    interpreter = Interpreter(output=lambda _text: None)
    observed = []
    for _sample in range(SAMPLES):
        started = perf_counter_ns()
        for _iteration in range(ITERATIONS):
            if interpreter.eval(PROGRAM) != 104:
                raise RuntimeError("semantic guard failed")
        observed.append(perf_counter_ns() - started)
    print(f"samples_ns={observed}")
    print(f"median_ns={median(observed)}")
    print(f"iterations_per_sample={ITERATIONS}")


if __name__ == "__main__":
    main()
