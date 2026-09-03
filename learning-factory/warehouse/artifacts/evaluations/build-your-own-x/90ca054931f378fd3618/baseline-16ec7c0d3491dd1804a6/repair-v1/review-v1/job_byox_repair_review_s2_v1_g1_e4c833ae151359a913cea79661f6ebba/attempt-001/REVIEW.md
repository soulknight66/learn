# Independent review

Verdict: **REVISE**. The educational design and reference behavior are strong,
but the submitted reproduction path has one blocking build defect and its pack
verifier has an avoidable coverage hole. This verdict is advisory and does not
promote any validation label.

## Prioritized findings

### P1 — The documented clean build cannot find the configured linker

`CANDIDATE/starter/Makefile:1-3`,
`CANDIDATE/sealed/reference/Makefile:1-3`, and
`CANDIDATE/sealed/reference_tests/Makefile:1-3` pin the GCC driver but do not bind its
Binutils programs. In the provided minimal environment, that driver reports
`ld` for `-print-prog-name=ld`, and `ld` is intentionally absent from `PATH`.
Both documented clean builds compiled every object and then failed at the link
step with:

```text
collect2: fatal error: cannot find 'ld'
```

This contradicts the reproducibility implied by
`CANDIDATE/environment/README.md:15-20` and prevents the learner quick start at
`CANDIDATE/README.md:26-31`. It also makes the statement in
`CANDIDATE/VALIDATION.md:32-33` that no other configured toolchain root was
needed incomplete: some linker was necessarily an implicit dependency in the
builder environment.

The same sources built and tested successfully when GCC was invoked with:

```text
-B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/
```

Required revision: bind the configured Binutils directory deterministically in
all three Makefiles (while preserving a documented override), make the
environment check perform a bounded link smoke test rather than only
`-fsyntax-only`, record GNU ld's exact path/version, and regenerate the builder
evidence using the documented commands in a minimal environment.

### P2 — The archive verifier does not inspect unexpected top-level entries

`CANDIDATE/sealed/reference_tests/verify_pack.py:119-129` builds its scan set
from known top-level required files plus eight managed directories. It never
walks or rejects any other top-level entry. In a scratch copy, an unexpected
top-level text file matching the verifier's own credential regex was added;
the verifier still exited 0 and printed `credential-pattern scan: PASS`. The
fixture was removed after the check, and the submitted candidate itself has no
such entry.

This does not establish a present leak, but it makes the claimed archive
boundary check fragile against future additions and weakens the durable safety
guard. Required revision: traverse the entire archive root and either reject
entries outside an explicit allowlist or apply entry-type and credential scans
to every entry. Add a regression test for an unexpected top-level file and
symlink.

## Confirmed strengths

- After explicitly binding GNU ld 2.43, strict C17 normal builds succeeded.
  The starter passed its two lexer checks with eight intentional language-test
  skips. The sealed reference passed 10 public tests, 26 direct VM checks, and
  18 private methods.
- Nine separate reviewer-authored boundary probes passed, including exact
  identifier/local/source/code limits, short-circuit fault suppression,
  normalized logical values, non-ASCII rejection, and opcode-only budget
  accounting.
- The ASan/UBSan rerun passed the same 26 + 10 + 18 checks without a sanitizer
  diagnostic. Leak detection was disabled, so this is not leak evidence.
- The tower result was exactly `4242\n`. Direct overflow and zero-budget probes
  produced the required source-located, single-line runtime errors.
- The specification is unusually clear about grammar, deterministic ceilings,
  bytecode, error prefixes, and the limited meaning of the tower. Starter
  milestones, concepts, design questions, adversarial prompts, and sealed
  explanations provide useful progressive learning material.
- The reference source statically checks stack/local/heap/jump/operand bounds,
  arithmetic faults, syntax depth, and execution budget. Test subprocesses use
  argument arrays, captured output, and timeouts.
- Manifest claims are restrained: only `GENERATED` and `PARTIAL` are present,
  independent validation remains required, and productionization is false.
  Builder prose explicitly avoids claiming factory validation, fuzzing,
  benchmarking, leak checking, or transfer verification.
- `LICENSE_BOUNDARY.md` clearly separates the CC0 catalog metadata from the
  linked tutorial's `NOASSERTION` license and makes no permission claim for the
  linked work. Manifest/provenance identity fields are internally consistent.

## Publication and evidence boundaries

The full submitted archive intentionally contains `sealed/`, including the
reference implementation, design answers, and private tests. The public docs
identify that boundary clearly, and no sealed/reference/answer material was
found elsewhere in the current tree. Nevertheless, no learner projection or
orchestrator-captured transfer check was available here. Do not publish the
full archive, and do not infer `TRANSFER_VERIFIED` from this review.

The upstream repository/snapshot was unavailable and network access was
restricted, so independent authorship, the recorded upstream commit, and
third-party licensing could not be corroborated beyond internal provenance
consistency. No `REVIEWED`, `TESTED`, `FUZZED`, `BENCHMARKED`,
`TRANSFER_VERIFIED`, or `PRODUCTIONIZED` label is conferred by these results.
