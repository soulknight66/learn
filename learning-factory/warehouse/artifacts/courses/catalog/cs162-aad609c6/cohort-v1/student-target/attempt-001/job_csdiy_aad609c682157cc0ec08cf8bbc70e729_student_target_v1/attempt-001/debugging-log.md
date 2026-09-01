# Debugging Log

This log records observable engineering decisions and experiments, not private reasoning.

## 1. Warning-clean vertical build

- Command: `make clean && make`
- Hypothesis: module declarations and ownership interfaces compile as strict C17 without diagnostics.
- Result: status 0 under `-std=c17 -Wall -Wextra -Wpedantic`; no compiler warnings.
- Lesson: compiling the module skeleton before documentation caught interface risk early, although no compiler defect appeared.

## 2. First unattended test run

- Command: `make test`
- Result: status 2; all attempted subprocess cases errored before invoking `rrsim` because Python 3.6 rejected `capture_output=True`.
- Action: replaced `capture_output` with explicit `stdout=subprocess.PIPE` and `stderr=subprocess.PIPE`.
- Lesson: the harness runtime is part of the supported environment.

## 3. Second harness compatibility failure

- Command: `make test`
- Result: status 2; Python 3.6 also rejected `text=True`.
- Action: replaced it with `universal_newlines=True` and retained the subprocess timeout.
- Lesson: fixing the first reported incompatibility did not justify assuming adjacent APIs were supported.

## 4. Contract-suite run and oracle audit

- Command: `make test`
- Result: the initial 15 tests passed after the compatibility fixes.
- Experiment: expanded the suite with public-limit cases, the 128/129-task boundary, embedded NUL rejection, and 80 cases from a separately written seeded event model.
- Command: `make clean && make test`
- Result: status 0; all 19 named tests passed, including every seeded subcase.
- Lesson: stable arrival ordering and exact-boundary behavior should be tested both with minimal hand oracles and broader differential cases.

## 5. Memory-safety tooling

- Command: `make sanitize-test`
- Hypothesis: the compiler installation includes linkable AddressSanitizer and UndefinedBehaviorSanitizer runtimes.
- Result: status 2 at link time: `/usr/bin/ld` could not find `libasan.so.5.0.0` or `libubsan.so.1.0.0`; no instrumented tests ran.
- Follow-up: `command -v valgrind`, `command -v gdb`, and `command -v clang` each found no installed tool. GCC also reported no installed static sanitizer archive path.
- Action: recorded the limitation and returned to a clean normal C17 build. No memory-safety/debugger success is claimed.

## 6. Final reproducibility check

- Experiment: tried to capture a quieter build from a non-login shell.
- Result: `make` failed with status 2 because `cc` could not locate its internal `cc1` executable in that reduced environment.
- Action: used the provided login-shell environment, where the documented commands succeeded. Its startup emitted UID/GID name-resolution warnings, which are retained in `EVIDENCE.txt` and are separate from compiler/test diagnostics.
- Final result: the clean build and unattended suite succeeded. Their exact statuses and output are recorded in `EVIDENCE.txt`. Generated build products are removed after evidence capture so a future evaluator starts from source.
