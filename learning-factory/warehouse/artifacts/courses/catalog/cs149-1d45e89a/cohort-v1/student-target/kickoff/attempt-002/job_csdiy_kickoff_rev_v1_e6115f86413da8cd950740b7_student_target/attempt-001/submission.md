# Revised bounded kickoff submission

This submission contains only the supplied trustworthy-parallel-histogram
kickoff. It is not a claim of completing CMU 15-418, Stanford CS149, or any
whole course. Independent validation—not this summary—determines acceptance.

## Revision outcome

The prior attempt failed because its artifact map referred to files that were
not transferred. In this staged workspace, the referenced implementation and
evidence are now present as files rather than narrative claims. The revision
also adds captured staged-copy validation logs and a SHA-256 manifest. This does
not claim that a separate examiner workspace has received or verified them.

## Artifact map

- `CMakeLists.txt`, `include/histogram.hpp`, `src/histogram.cpp`,
  `src/main.cpp`: reproducible C++17 build, public API, sequential oracle,
  private-histogram `std::thread` implementation, and deterministic CLI.
- `tests/histogram_tests.cpp`: known-value, boundary, seeded, skewed,
  excessive-thread, invalid-thread, conservation, and injected-worker-failure
  checks.
- `README.md`: exact clean-build, CTest, correctness, benchmark, manifest, and
  optional-sanitizer commands.
- `DESIGN.md`: contract, invariants, work/span model, ownership proof,
  pre-measurement predictions, rejected alternative, and marked revisions.
- `benchmark_raw.csv`: 54 raw measured rows, each with input/thread provenance,
  integer durations, derived fields, oracle/conservation booleans, and an
  explicit validation label.
- `benchmark_metadata.json`: machine/build/method provenance, six exact
  commands, timed-region definition, and observed-release validation label.
- `REPORT.md`: robust summaries, scoped performance claim, uncertainty,
  possible explanations, limitations, and one unperformed next experiment.
- `COMPREHENSION_ANSWERS.md`: answers to all ten supplied prompts.
- `validation/`: configure, build, CTest, boundary, data-consistency, and failed
  supplemental-sanitizer records from this staged copy.
- `ARTIFACT_MANIFEST.sha256`: hashes for every other submission artifact above,
  including the fresh `notes.md`, `submission.md`, and `debugging-log.md` (a
  manifest cannot recursively hash its own final contents).

## Reproducible validation route

```bash
sha256sum -c ARTIFACT_MANIFEST.sha256
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure
./build/histogram_cli check --size 4099 --seed 24301 --threads 7
```

Observed from a separate clean `verify-build` directory in this staged root:
configuration and compilation succeeded with GCC 8.5.0 and no warning output;
4/4 CTest entries passed in 0.08 seconds; explicit checks for `N=3,T=8`,
`N=0,T=8`, and `N=4099,T=7` matched all 256 bins and conserved the input.
The zero-thread route returned status 2. The durable command outputs are under
`validation/`.

The system CMake packaging in this restricted workspace could not locate its
installed module tree. Validation used a disposable copy of the same CMake
3.26.5 binary pointed at `/usr/share/cmake`; it did not alter project files or
compiler flags. This environment-specific observation is preserved in
`validation/tooling-and-sanitizers.log` rather than hidden.

## Evidence boundary

Every retained benchmark row passed its in-process oracle and conservation
checks, and a separate consistency calculation checked row counts and derived
fields. Performance remains specific to one uncontrolled worker. Sanitizer
executables could not link because the local runtime libraries were absent, so
the safety case is the explicit ownership/memory-model audit plus deterministic
functional tests, not a claimed sanitizer pass.

Scratch builds are reproducible and are not submission artifacts. No optional
external reference or answer-bearing implementation was used.
