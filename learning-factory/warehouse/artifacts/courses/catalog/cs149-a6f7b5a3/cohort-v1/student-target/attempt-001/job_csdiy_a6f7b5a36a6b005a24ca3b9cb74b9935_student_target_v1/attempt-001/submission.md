# Bounded kickoff submission

This is an attempt at only the supplied parallel-histogram kickoff/first unit.
It is not a claim of completing CMU 15-418, Stanford CS149, or any whole course.
Independent validation, not this summary, determines whether the unit artifacts
are acceptable.

## Artifact map

- `include/histogram.hpp`, `src/histogram.cpp`: testable sequential oracle and
  `std::thread` implementation with private counters and exception propagation.
- `src/main.cpp`: deterministic correctness and bounded benchmark CLI.
- `tests/histogram_tests.cpp`, `CMakeLists.txt`: dependency-light build and
  deterministic unit/CLI tests.
- `README.md`: exact clean-build, test, correctness, benchmark, and optional
  sanitizer commands.
- `DESIGN.md`: stable contract, invariants, ownership audit, work/span model,
  predictions, rejected alternative, and marked revisions.
- `benchmark_raw.csv`, `benchmark_metadata.json`: 54 raw measured rows with
  generator provenance, machine/build/method metadata, and explicit oracle,
  conservation, and validation labels.
- `REPORT.md`: machine/build context, robust summaries, scoped claim,
  limitations, and one unperformed next experiment.
- `COMPREHENSION_ANSWERS.md`: responses to all ten supplied prompts.
- `notes.md`, `debugging-log.md`: hypotheses, experiments, failures, and lessons.

## Reproducible validation route

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure
./build/histogram_cli check --size 4099 --seed 24301 --threads 7
./build/histogram_cli benchmark --size 4000000 --seed 24301 --threads 4 --repetitions 9
```

Observed in this workspace: the warning-enabled release build succeeded; all
four CTest entries passed in both the working build and a fresh verification
build; explicit empty and excessive-thread checks matched the sequential
oracle; and every retained benchmark row matched all 256 bins and conserved the
input size. A separate consistency check parsed the metadata and validated the
54 CSV rows and their derived fields. Scratch build directories were removed
afterward and can be regenerated with the commands above.

## Evidence boundary

ThreadSanitizer and UndefinedBehaviorSanitizer were attempted but could not link
because their runtime libraries were absent. The performance samples were also
noisy on an uncontrolled shared worker. Those are retained limitations, not
converted into success claims. No optional external reference was used.
