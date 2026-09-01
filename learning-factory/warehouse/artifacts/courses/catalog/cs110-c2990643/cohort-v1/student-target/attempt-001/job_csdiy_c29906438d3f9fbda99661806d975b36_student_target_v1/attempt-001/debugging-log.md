# Debugging log

This is an observation log, not private reasoning. Each entry records a concrete
hypothesis, command/experiment, result, and resulting change or lesson.

## 1. Warning-clean initial build

- **Hypothesis:** The initial C++17 end-to-end implementation would compile with
  warnings treated as errors.
- **Experiment:** `make -C submission clean all`.
- **Observed:** Compilation succeeded with `-Wall -Wextra -Wpedantic -Werror`.
  The first clean emitted a harmless, ignored `rmdir` error when `build/` did not
  yet exist.
- **Change:** Made the empty-directory removal quiet while leaving the targeted
  clean behavior intact. Added explicit `<algorithm>` and `<type_traits>`
  includes instead of depending on transitive standard-library includes.

## 2. First integration run failed in the harness

- **Hypothesis:** The Python standard-library tests would exercise the compiled
  binary.
- **Experiment:** `make -C submission test`.
- **Observed failure:** All nine tests stopped before launching `proc-run` with
  `TypeError: __init__() got an unexpected keyword argument 'text'`. The local
  interpreter identifies its subprocess implementation as Python 3.6.
- **Diagnosis:** `text=True` is newer spelling for text-mode pipes and is not
  accepted by this interpreter. This was a harness portability failure, not nine
  independent supervisor failures.
- **Change:** Replaced it with the compatible
  `universal_newlines=True` argument in both launch sites.

## 3. Clean rebuild and complete suite

- **Experiment:**

  ```sh
  make -C submission clean all
  make -C submission test
  ```

- **Observed:** The clean build succeeded and all 9 tests passed in 2.192 seconds
  on the first corrected run. Covered outcomes were normal exit, status 37,
  `SIGUSR1`, literal arguments, failed `exec`, rejected zero timeout, direct
  timeout, descendant group signalling, and 20 repeated quick exits.
- **Lesson:** A test harness's runtime version is part of the maintained platform
  contract; standard-library-only does not imply version-independent syntax.

## 4. Syscall-tracing attempts were blocked

- **Hypothesis:** Installed `strace` could show the failed-exec lifecycle.
- **Experiment:** Ran `strace -f` with process, descriptor, and signal events
  around an invocation of a nonexistent executable.
- **Observed failure:** `PTRACE_TRACEME: Operation not permitted`, followed by a
  denied `PTRACE_SETOPTIONS`. The target lifecycle did not run under the tracer.
- **Second experiment:** `perf trace` on the same path.
- **Observed failure:** exit 255; its output file said debugfs/tracefs could not
  be found or mounted.
- **Lesson:** Tool binaries being present does not establish that the sandbox or
  kernel exposes their tracing mechanisms. These attempts are not represented
  as successful traces.

## 5. Sanitizer attempts lacked runtimes

- **Hypothesis:** A sanitizer debug build could provide a fallback inspection.
- **Experiments:** Compiled once with `-fsanitize=address,undefined` and once with
  `-fsanitize=undefined`.
- **Observed failures:** The linker could not find
  `/usr/lib64/libasan.so.5.0.0` or `/usr/lib64/libubsan.so.1.0.0`, respectively.
- **Change:** Did not weaken or alter the release build to accommodate absent
  optional runtimes; selected the installed GCC coverage tool instead.

## 6. Coverage inspection of failed `execvp`

- **Hypothesis:** GCC coverage can verify the parent's failure-path transitions
  without requiring tracing privileges.
- **Experiment:** Built `proc_run.cpp` with `-O0 -g --coverage`, invoked
  `/definitely/not/a/proc-run-program`, then ran `gcov -b -c`.
- **Observed:** The invocation returned 127 and printed
  `proc-run: child execvp failed: No such file or directory`. `gcov` recorded two
  calls to `wait_without_blocking`, one reaped branch, one call to
  `finish_result`, one complete child-report branch, and the status-127 branch.
  The requested child stderr file was empty.
- **Limitation of evidence:** The pre-exec child correctly ends with `_exit`, so
  it does not flush its own coverage counters. Parent-side consumption of the
  fixed error record and the integration assertion are evidence for that side of
  the protocol; child line coverage is not claimed.

## 7. Timing-margin review

- **Hypothesis:** A tight elapsed-time upper assertion would create needless
  failures on a loaded worker.
- **Experiment:** Reviewed the timeout tests after the passing run.
- **Change:** Kept a loose lower bound (60 ms for a requested 120 ms deadline)
  and used the independent four-second `subprocess` timeout as the bounded hang
  detector. Increased the descendant startup timeout to two seconds and removed
  an aggregate speed assertion from repeated quick runs; every individual run
  remains bounded by three seconds.
- **Lesson:** Correct timeout tests distinguish semantic bounds from performance
  expectations and ensure that failure remains finite.

## 8. Final clean validation

- **Experiment:** Repeated the documented clean build and complete test command
  after the timing-margin edits.
- **Observed:** Compilation again passed with warnings as errors; all 9 tests
  passed in 3.473 seconds.
- **Layout check:** Python 3.6 had generated a `tests/__pycache__` directory.
  Added `PYTHONDONTWRITEBYTECODE=1` to the test recipe and removed that scratch
  cache. A second clean build/test after that Makefile change passed all 9 tests
  in 3.126 seconds and did not recreate the cache.
