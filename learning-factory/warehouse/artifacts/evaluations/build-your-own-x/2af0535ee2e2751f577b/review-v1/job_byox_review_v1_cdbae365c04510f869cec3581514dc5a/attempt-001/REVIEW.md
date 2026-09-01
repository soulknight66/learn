# Independent review

## Verdict

**REVISE.** Keep the artifact at `GENERATED` + `PARTIAL`. It is a thoughtful and unusually candid
challenge pack, but it is not ready for learner release until the correctness and isolation issues
below are addressed.

## Prioritized findings

### P1 — Valid, in-limit source can crash the reference compiler

The expression parser recurses through `primary()` for every parenthesized expression. An independent
probe succeeded through depth 4,096, but a valid 32,776-byte program at depth 16,384 terminated with
SIGSEGV (`returncode=-11`). This input is far below the documented 1 MiB CLI ceiling and violates the
expectation that valid source receives a `PebbleResult` instead of killing the process.

The candidate honestly discloses this in `sealed/REVIEW.md`; disclosure does not make the reference a
safe oracle. Add an explicit syntactic-depth limit (returning a deterministic limit error) or use an
iterative parser, and test immediately below and above the boundary for parentheses, unary chains,
and nested blocks.

### P1 — The lexer debugging exercise teaches a nonexistent memory-safety bug

`debugging/lexer/buggy_keyword.c` passes `length` as the bound to
`strncmp(start, "let", length)`. It does misclassify the shorter identifiers `l` and `le` as `let`,
which the independent probe confirmed. It does **not** read beyond a valid `length`-byte token slice,
and `strncmp` stops at the string literal's NUL; the token slice need not be NUL-terminated. Both the
exercise prompt and sealed answer assert otherwise.

Replace the buggy fragment with one that really has both intended defects—for example, an unchecked
three-byte comparison that both reads short slices and accepts longer `let...` identifiers—or narrow
the prompt and answer to the actual prefix-classification defect.

### P1 — CLI input handling loses bytes and does not enforce the regular-file boundary

The file reader records a byte count but passes only a NUL-terminated pointer to the compiler. A file
containing `print 1;\0print 2;` exited 0, printed `1`, and silently ignored everything after the NUL.
Under the lexical rules, an unrecognized source byte should be diagnosed, not reinterpreted as EOF.
The reference also accepted `/dev/null` as an empty source even though `REQUIREMENTS.md` calls for a
regular input path. A FIFO can consequently block before the byte limit helps.

Reject embedded NUL bytes before compilation (or make the compiler length-aware), and open then
`fstat` the descriptor before bounded reading. Clarify whether embedded NUL is rejected at the CLI
boundary because the public C API is necessarily string-based.

### P1 — Progressive disclosure is organized but not enforced or transfer-verified

The static separation is good: learner work is under `starter/`, and answers are nested under clearly
named `sealed/` children. However, every answer, hidden test, production note, and the complete
reference implementation is readable in the submitted tree. `AGENTS.md` instructions are policy, not
an access boundary. No deterministic command creates an allowlisted learner view, and no evidence
shows that a transferred view excludes `sealed/`, `adversarial/`, exercise answer children, and other
evaluator-only material.

Do not distribute the whole tree. Add a harness-controlled view manifest/projector plus a test that
enumerates the resulting learner artifact and rejects every evaluator-owned path and solution marker.

### P1 — Evaluator subprocesses are not fully bounded or contained

`benchmarks/run.py` has no subprocess timeout. The public and adversarial Python runners use argv
arrays and per-call timeouts, but do not create and terminate a process group, and their captured
stdout/stderr are not size-bounded. A learner executable that forks, hangs, or floods output can outlive
the immediate timeout or consume unbounded harness memory. The direct C harness invocation in the
Makefile is also unbounded.

Route all learner executables through one harness-owned runner with a new process group, deadline,
group kill/reap, and capped logs. Give the benchmark a timeout even though it makes no performance
claim.

### P2 — Redistribution rights for the generated material are unresolved

The boundary is described honestly: CC0 applies to catalog metadata, while the separately linked work
is `NOASSERTION` and is claimed not to have been copied. But there is no `LICENSE` or SPDX grant for
the generated code, tests, or prose; `LICENSE_BOUNDARY.md` explicitly tells redistributors to perform
their own assessment. That is not evidence of wrongdoing, but it is a release blocker wherever the
pack must be copied to learners. Obtain an appropriate grant or explicitly constrain the deployment
to an authorized use context.

### P2 — Normative behavior and learner feedback need sharper boundaries

Two contract areas remain implementation-dependent:

- Negative division and remainder use C11 truncation in the reference, but the language requirements
  do not state quotient rounding or remainder-sign semantics.
- Public options expose code, constant, symbol, stack, and instruction-step limits while internal
  bytecode representation is deliberately left open. Exact limit behavior can therefore differ across
  otherwise conforming implementations.

Define these observables independently of the reference representation. Also add staged public tests
for the normative C API, compile-failure atomicity, repeated execution, and caller limits. The current
11 public tests are CLI-only and combine several milestones, so feedback is coarse for a learner
starting from a 56-line placeholder.

### P2 — Provenance is internally consistent but does not make the generated tree reproducible

The project/source/commit identifiers match, and the audit's canonical provenance hash is correct.
The manifest field named `provenance_sha256` is the embedded source snapshot identifier, not the byte
or canonical hash of `PROVENANCE.json`. There is also no digest inventory for the 52 generated files,
generator identity/version, or deterministic regeneration recipe. The self-audit can therefore pass
after substantive source changes so long as its small metadata object and path rules still match.

Record a canonical provenance-object digest and a generated-artifact manifest (path, digest,
classification, and validation label), and document what is and is not reproducible. Two clean builds
were byte-identical on this host, but that is only same-host evidence.

## Evidence that held up

- The starter and reference built cleanly as C11 with the stated warning policy on a scratch copy.
- The submitted reference suites produced the documented counts: 11 public, 18 boundary, 16 API, and
  7 deterministic adversarial tests all passed.
- Independent checks passed for five semantic/atomicity scenarios, 18 API properties, and 500 signed
  arithmetic boundary combinations.
- The requirements, concept map, design questions, tradeoff discussion, and production-gap list are
  substantive and useful. The starter failure is clearly intentional rather than disguised as a
  completed implementation.
- Validation-label honesty is strong: no fuzz, benchmark-result, production, transfer, or independent
  review claim is made, and sanitizer failure is reported as unavailable rather than passed.
- Internal manifest/provenance identifiers match; the candidate contains 52 regular files, no
  symlinks, and no obvious credential artifact. The linked tutorial remains a provenance pointer.

These positives justify revision rather than rejection, but the passing submitted suites do not
override the independently observed failures.
