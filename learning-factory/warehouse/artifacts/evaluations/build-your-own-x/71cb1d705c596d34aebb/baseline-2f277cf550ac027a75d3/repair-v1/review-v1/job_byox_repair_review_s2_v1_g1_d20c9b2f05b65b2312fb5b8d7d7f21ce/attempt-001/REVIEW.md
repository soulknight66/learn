# Independent review

Verdict: **REVISE**. The candidate is unusually candid and most builder evidence
reproduces, but two reference-contract defects and two learner-harness defects
need correction before advisory approval.

## Prioritized findings

### P1 — Foreground children retain inherited blocked terminal signals

`child_signal_defaults()` in
`CANDIDATE/sealed/reference/src/msh.c:484` changes signal dispositions but never
clears the inherited signal mask. A reviewer PTY check blocked `SIGINT` before
executing `msh`, started `/bin/sleep 10`, and sent Ctrl-C. The terminal echoed
`^C`, but no new prompt arrived within the one-second deadline; bounded cleanup
then killed the test processes. This violates the requirement that children
restore default `SIGINT` behavior and breaks core interactive job control for a
valid inherited process state.

Unblock the listed job-control signals in the child before a built-in or
`execvp`, check setup errors, and add an inherited-blocked-mask PTY regression.

### P1 — Ordinary harness timeouts do not contain descendant processes

The public, sealed, and adversarial runners call `subprocess.run(...,
timeout=...)` without creating a process group or performing group cleanup
(`CANDIDATE/public_tests/test_shell.py:23`,
`CANDIDATE/sealed/reference_tests/test_reference.py:21`, and
`CANDIDATE/adversarial/test_boundaries.py:14`). This violates the repository's
process-group invariant for subprocesses. A controlled target forked one
sleeping descendant: `run_command(..., timeout=0.3)` returned after 0.303 s, but
the probe reported `descendant_alive=True`. The reviewer immediately sent that
descendant `SIGKILL`.

A broken learner shell can therefore leak children after a test timeout. Start
each target in an isolated process group/session and use bounded TERM/KILL group
cleanup. Apply the same rule to the optional benchmark driver.

### P2 — A newline-delimited line of exactly 1 MiB is rejected

The contract permits rejection only when the input line is *larger* than 1 MiB.
In `CANDIDATE/sealed/reference/src/msh.c:1070`, `getline`'s length is compared
before the delimiting LF is removed. An independently generated command of
exactly 1,048,576 bytes plus LF returned 2 with `input line exceeds 1 MiB`; the
identical bytes at EOF returned 0. Exclude the delimiter from the size test and
add exact-boundary cases with and without LF.

### P2 — The advertised `make check` path selects an unsupported Python

`CANDIDATE/starter/Makefile:20` invokes literal `python3`. In the supplied
managed PATH this is `/usr/bin/python3` 3.6.8, while the public suite uses APIs
not present there (`text=` and `os.waitstatus_to_exitcode`). Consequently,
`make -C starter check` produced 11 errors rather than meaningful expected
starter failures. The separately documented pinned Python 3.11.5 command works.

Make the runner configurable (for example, a documented `PYTHON` variable),
select the pinned interpreter in this environment, and state the minimum Python
version.

### P3 — Generated-material reuse terms remain unspecified

`CANDIDATE/LICENSE_BOUNDARY.md` correctly separates CC0 catalog metadata from a
linked resource whose license is `NOASSERTION`, but “intended for personal
educational use” is not an explicit license grant for the generated prose,
starter, reference, or tests. Add an actual license/SPDX declaration or state
the intended permissions and restrictions unambiguously.

## What held up

- Both C trees build warning-clean with the declared compiler and flags.
- The claimed 11 public, 16 sealed, and 4 adversarial reference tests pass, as
  do the same suites under ASan/UBSan; GCC `-fanalyzer` is clean.
- The intentionally incomplete starter and its failing-test count are disclosed
  accurately. The manifest does not overclaim `BUILDS`, `TESTED`, `FUZZED`,
  `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`.
- Milestones, observable requirements, concepts, design questions, debugging
  exercises, and tradeoff notes provide strong instructional progression.
- Sealed material is structurally confined to named instructor directories,
  and no symlinks or special entries were present.
- The provenance document's direct digest and all internal identity fields
  match the recorded values.

## Inconclusive boundaries

The external source snapshot and linked tutorial were unavailable, so their
hash/license and the claim of no copied material cannot be independently
verified. Likewise, this workspace contains the full instructor pack but no
orchestrator-produced learner view; actual exclusion of `sealed/` and
harness-only content is therefore not evidence-backed here. These limitations
preclude transfer or production claims regardless of this verdict.
