# Debugging and experiment log

Scope: the supplied kickoff revision only. Entries contain commands and
externally observable results, not private chain-of-thought. Read-only learner,
prior-attempt, and examiner-feedback files were not modified.

## 2026-08-31 — material and artifact discovery

`rg` was unavailable, so a bounded `find` inventory was used. The workspace
initially contained the three learner documents, three prior narrative files,
the examiner feedback, and job/workspace markers—none of the source or evidence
named by the prior submission. All supplied learner material, the prior
narratives, and `EXAMINER_FEEDBACK/feedback.md` were read. No rubric, hidden or
novel check, reference answer, other learner file, sealed material, or factory
state was searched for or inferred.

Action: create a fresh, self-contained project in the current staged root and
add a hash manifest; do not modify `PRIOR_ATTEMPT/` or claim that another
workspace has received it.

## 2026-08-31 — implementation and bounded tests

Implemented the C++17 interface, sequential oracle, private local histograms,
balanced contiguous partition, actual-worker clamping, join-before-merge, and
exception transport. The test-only failure seam names a worker that throws
before counting and uses the same launch/join/transport implementation.

The first ordinary test run passed, but its 0.90-second runtime exposed an
unnecessary test cost: large `T > N` cases created thousands of real threads.
The cases were revised to keep the same excessive-thread boundary with small
inputs while retaining large-input tests at modest thread counts. The resulting
release CTest run passed 4/4 in 0.05 seconds, and the later fresh staged-copy run
passed 4/4 in 0.08 seconds. This was a test-bounding change, not a correction to
histogram output.

## 2026-08-31 — CMake installation issue and release build

Initial command:

```text
cmake -S . -B work-build -DCMAKE_BUILD_TYPE=Release
```

Observed exit 1: CMake 3.26.5 reported `Could not find CMAKE_ROOT`; its expected
module path did not match the installed `/usr/share/cmake/Modules` tree. A
disposable workspace copy of the same binary was paired with a symlink to that
installed module directory. No project source or flag was changed by the
workaround.

The clean Release configuration then selected GNU C++ 8.5.0 and pthread. The
actual flags were:

```text
-O3 -DNDEBUG -std=c++17 -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion
```

All targets linked and no compiler diagnostic appeared.

## 2026-08-31 — correctness and failure behavior

Command:

```text
ctest --test-dir verify-build --output-on-failure
```

Observed: 4/4 entries passed in 0.08 seconds. The unit entry covered known
counts, empty/singleton/skewed cases, partition boundaries, four fixed seeds,
several thread counts, small `T > N` cases, conservation, zero-thread rejection,
and injected worker failure. CTest also exercised successful CLI partition and
empty cases plus CLI rejection of zero threads.

Additional observed outputs:

```text
N=3,T=8:    workers_used=3, match=true, conservation=true, exit=0
N=0,T=8:    workers_used=0, match=true, conservation=true, exit=0
N=4099,T=7: workers_used=7, match=true, conservation=true, exit=0
N=8,T=0:    error="--threads must be positive", exit=2
```

## 2026-08-31 — supplemental sanitizer attempts

Both `RelWithDebInfo` sanitizer configurations completed configuration and
object compilation. ThreadSanitizer executable links failed with
`/usr/bin/ld: cannot find /usr/lib64/libtsan.so.0.0.0`.
UndefinedBehaviorSanitizer links failed with
`/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0`. Both build commands
exited 2. No instrumented test executable existed, so neither attempt is
labeled as a pass. The ordinary suite remains independent of these optional
runtimes.

## 2026-08-31 — machine context and benchmark

Ordinary tools reported RHEL 8.10, Linux
`4.18.0-553.el8_10.x86_64 x86_64`, glibc 2.28, and 16 online logical
processors. Processor model, cache topology, and exclusive ownership were not
available within the restricted workspace. The machine is treated as
shared/uncontrolled, and the requested-thread cap was four.

After correctness passed, the Release CLI ran sizes 4,000,000 and 32,000,000,
seed 24301, and requested thread counts 1, 2, and 4. Each of the six commands
used one untimed warm-up and nine measured repetitions. All commands exited 0;
all 54 retained rows reported `oracle_match=true`, `conservation=true`, and
`oracle_and_conservation_checked`.

Median paired speedups were 0.803, 1.271, and 1.264 at 4 MB for one, two, and
four workers; at 32 MB they were 0.778, 1.313, and 1.379. The 32 MB/two-worker
range was 0.749–1.981, while four-worker median throughput (2.401 GB/s) did not
exceed two-worker median throughput (2.459 GB/s). The raw variability was kept;
no monotonic-scaling conclusion or algorithm change was manufactured from it.

## 2026-08-31 — staged-copy validation

A second clean `verify-build` directory was configured from the current staged
root, built, and tested. Configure, build, CTest, boundary outputs, and the
expected invalid exit are captured under `validation/` with explicit labels.
A standard-library CSV check found exactly 54 rows in the six expected groups,
nine repetitions each, validated all row labels/booleans, and recomputed every
speedup and throughput value within printed precision.

The final artifact inventory is hashed in `ARTIFACT_MANIFEST.sha256`. Hash
verification is run only after all listed files are final. Scratch build and
local-tool directories are excluded from the manifest and removed after
validation; they contain no durable evidence.
