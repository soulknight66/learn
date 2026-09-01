# Debugging and experiment log

Scope: the supplied kickoff unit only. Entries report commands and externally
observable results; they do not contain private chain-of-thought.

## 2026-08-31 — input/tool discovery

- `rg --files` failed because `rg` was not installed. A shallow filename-only
  listing was used instead. Only `COURSE_BRIEF.md`, `STUDY_TASK.md`, and
  `COMPREHENSION.md` were opened as course inputs.
- No external site, solution repository, rubric, sealed reference, factory
  state, or other learner's work was searched or read.

Lesson: an unavailable convenience tool should change the local command, not
expand the material boundary.

## 2026-08-31 — release build

Commands:

```text
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
```

Observed: configuration selected GNU C++ 8.5.0 and found pthread support. All
three targets built. The configured Release flags were `-O3 -DNDEBUG`; project
warning flags were also active. No compiler warning or error was emitted.

## 2026-08-31 — deterministic tests

Command:

```text
ctest --test-dir build --output-on-failure
```

Observed: 4/4 CTest entries passed in 0.05 seconds. The library harness exercised
known counts, empty/singleton/skewed inputs, sizes around partition boundaries,
three fixed seeds, multiple thread counts, `T > N`, conservation, zero-thread
rejection, and an injected exception from worker 2. CLI tests exercised a
deterministic check and invalid arguments.

Additional boundary experiments:

```text
./build/histogram_cli check --size 3 --seed 24301 --threads 8
./build/histogram_cli check --size 0 --seed 24301 --threads 8
./build/histogram_cli check --size 4099 --seed 24301 --threads 7
```

Observed used-worker counts were 3, 0, and 7 respectively. All three returned
status 0 with `match:true` and `conservation:true`.

No correctness-test failure occurred during this implementation, so no source
bug or corrective patch is invented for this log.

## 2026-08-31 — sanitizer failures

ThreadSanitizer experiment:

```text
cmake -S . -B build-tsan -DCMAKE_BUILD_TYPE=RelWithDebInfo -DENABLE_TSAN=ON
cmake --build build-tsan --parallel 2
```

Configuration and compilation succeeded, but both executable links failed:

```text
/usr/bin/ld: cannot find /usr/lib64/libtsan.so.0.0.0
collect2: error: ld returned 1 exit status
```

UndefinedBehaviorSanitizer experiment:

```text
cmake -S . -B build-ubsan -DCMAKE_BUILD_TYPE=RelWithDebInfo -DENABLE_UBSAN=ON
cmake --build build-ubsan --parallel 2
```

It failed at the corresponding link stage:

```text
/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0
collect2: error: ld returned 1 exit status
```

Diagnosis: the compiler accepts instrumentation flags, but the environment
lacks the runtime shared objects. Result: sanitizer evidence is unavailable;
neither attempt is labeled as a passed run. The ordinary suite remains the
portable required evidence.

## 2026-08-31 — machine metadata limitation

`uname -srm` reported Linux `4.18.0-553.el8_10.x86_64 x86_64`, and
`getconf _NPROCESSORS_ONLN` reported 16. `lscpu` failed because its expected CPU
system path was unavailable, so no processor model or cache topology is
reported. The benchmark cap was set to four to keep the shared run bounded.

## 2026-08-31 — benchmark and unexpected variability

For each size in 4,000,000 and 32,000,000 bytes and each thread count in 1, 2,
and 4, the release CLI ran one warm-up and nine repetitions with seed 24301.
All six commands returned status 0. The 54 unrounded duration pairs are retained
in `benchmark_raw.csv`; all validation labels say observed release run, and all
oracle/conservation fields are true.

Observation that challenged the initial scaling hypothesis: at 4 MB/four
threads, paired speedup ranged from 0.639 to 1.457. At 32 MB/four threads it
ranged from 0.858 to 1.779. Sequential durations also shifted markedly within
some runs. This is consistent with material environmental noise, although the
experiment cannot identify its cause.

Decision: preserve the data, report medians and full ranges, and avoid changing
the algorithm based on an unstable benchmark. A more controlled rerun is
proposed in `REPORT.md` but was not performed.

## 2026-08-31 — final reproducibility checks and cleanup

A new `verify-build` directory was configured from source, compiled, and tested
with the README's Release workflow. It again passed 4/4 CTest entries (0.06
seconds). A separate read-only consistency check parsed
`benchmark_metadata.json`, found exactly 54 CSV rows in six configurations of
nine, recomputed every speedup and throughput within the printed precision, and
confirmed all validation labels.

The generated `build`, `build-tsan`, `build-ubsan`, and `verify-build`
directories were then explicitly removed. They contained only reproducible
scratch build products; source and all durable success/failure evidence remain.
