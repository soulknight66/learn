# Test Report

## Environment

Commands were run on 2026-08-31 from the `submission/` directory. No network or
external course material was used.

- `cc --version`: GCC 8.5.0 20210514 (Red Hat 8.5.0-22)
- `make --version`: GNU Make 4.2.1
- `python3 --version`: Python 3.6.8
- production flags shown by the build: `-O2 -std=c11 -Wall -Wextra
  -Wpedantic -Werror`

The command harness printed warnings that the numeric user/group IDs had no
name. Those warnings preceded tool output and did not come from the build or
test subjects.

## Commands actually run and outcomes

1. `make test`

   The initial run compiled both C targets with the strict flags. The C module
   checks passed, then all 9 Python black-box test methods passed. The boundary
   method exercised four subcases.

2. `cc --version`, `make --version`, and `python3 --version`

   Each succeeded and produced the versions recorded above.

3. `make clean`

   Succeeded and removed only `build/`.

4. `make all`

   Succeeded from the clean state and produced `build/bytehist` without a
   warning promoted to an error.

5. `make test`

   Succeeded after the clean rebuild. The C module checks and all 9 Python test
   methods passed again; there were no skips.

6. `make clean`

   Succeeded before the diagnostic build experiment.

7. `make test CFLAGS='-O1 -g -fsanitize=undefined'
   LDFLAGS='-fsanitize=undefined'`

   Failed while linking `build/bytehist`. Compilation completed, but the linker
   reported `/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0`. No
   sanitizer-instrumented test ran, so this is recorded as an unavailable
   diagnostic rather than a pass.

8. `make clean`, followed by a final ordinary `make test`

   Recorded after the final run below: the clean succeeded; the strict ordinary
   build succeeded; the C module checks passed; and all 9 Python test methods
   passed with no skips.

9. Final `make clean`

   Recorded after the final cleanup below: succeeded, leaving no generated
   binary or object in the submission.

## Coverage and independent oracles

The black-box suite covers standard-input and named-file input; empty, ordinary,
NUL-containing, and high-byte data; exact row order and formatting; literal
`-` handling; exact usage failure; unavailable and non-regular inputs; sizes on
both sides of the 4096- and 8192-byte boundaries; and a closed output pipe. Its
expected reports are fixed literals or, for repeated-byte boundary inputs, a
simple closed-form count based on the chosen input length. It never imports or
reuses production counting code.

The separate C module check covers empty and ordinary state, bulk updates, the
`UINT64_MAX` limit, rejection of total and selected-counter overflow, and
nonmutation after rejection.

## Remaining limitations

- A failed close of an otherwise readable named input was not injected.
- Exact input lengths 4096 and 8192 were not tested; both adjacent sides were.
- Count overflow is infeasible to drive through a real input stream, so it is
  validated at the module contract instead.
- The UBSan runtime was unavailable, as recorded above. This report makes no
  sanitizer-pass claim.

---

Provenance: learner-authored from the three supplied kickoff files and the
command outputs listed here; no optional reference was consulted.

Validation label: `LEARNER_EXECUTED_TESTS_AWAITING_INDEPENDENT_VALIDATION`.
