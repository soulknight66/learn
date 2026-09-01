# Independent review

Verdict: **REVISE**. The pack is coherent, conservatively labeled, and largely reproducible, but
the sealed reference can crash on valid input that is still inside every advertised translation
limit. That blocks acceptance as a safe reference. The findings below are ordered by priority.

## 1. High — valid in-budget nesting can crash the reference

`REQUIREMENTS.md:29-42` requires implementations to accept the listed capacities safely and to
diagnose larger internal needs rather than corrupting memory. A reviewer-generated valid program
with 32,760 nested parenthesis pairs was only 65,550 bytes and had 65,534 language tokens (65,535
including the stored EOF marker). It is therefore below both the 1 MiB and 65,536-token limits and
emits only six bytecode instructions.

The normal strict `-O2` reference build terminated with signal 11, empty stdout, and empty stderr
in three of three focused executions with the environment's 8 MiB stack. The recursive path at
`sealed/reference/src/minic.c:502-504` re-enters every expression-precedence routine for each pair
of parentheses and has no parser-depth guard. Shallower results were stack-layout-sensitive: a
32,750-pair case sometimes succeeded and sometimes received signal 11.

Required revision: make parsing iterative where appropriate or enforce a deterministic nesting
limit before host-stack exhaustion, returning a source diagnostic. The supported limit must be
compatible with the advertised token capacity, or the normative capacity contract must be
changed and tested explicitly. Add this case to harness-controlled negative/boundary coverage.

## 2. Medium — timeout handling does not contain the tested process tree

`public_tests/run_tests.py:15-22` and `sealed/reference_tests/run_tests.py:17-24` call
`subprocess.run` with argv arrays, captured pipes, and per-case timeouts. Those are useful bounds,
but Python's timeout kills only the direct child here. Neither runner starts a new session nor
kills the child's process group. A tested executable can leave descendants alive and holding the
captured pipes. Captured stdout/stderr is also unbounded in memory.

This falls short of the repository rule that subprocesses use process groups and bounded captured
logs. Use a harness-controlled `Popen` session/process group, kill the group on timeout, reap it,
and impose output and aggregate resource limits. Candidate-authored runners remain supporting
material, not evidence for a TESTED label.

## 3. Medium — the token boundary is ambiguous and conventionally one short

The normative table promises capacity for 65,536 tokens (`REQUIREMENTS.md:35`). The reference
allocates exactly 65,536 slots (`sealed/reference/src/minic.c:19,118`) and routes the synthetic EOF
through the same full-table check (`sealed/reference/src/minic.c:190-204`). Consequently, a valid
program containing 65,535 language tokens succeeds, while one containing 65,536 language tokens
exits 65 with `too many tokens` before parsing.

If EOF is intended to count, the contract should say so. Under the usual reading that the source's
lexical tokens are counted separately from an implementation sentinel, the implementation is one
slot short. Reserve EOF separately or allocate one extra slot, then add exact and one-over tests.

## 4. Medium — the starter and reference disagree on budget syntax

The starter uses `strtoumax` in `starter/src/main.c`, which accepts leading whitespace and a
leading plus sign. Reviewer runs showed that both `--max-steps +1` and `--max-steps ' 1'` reached
the starter interpreter with budget 1 (exit 65), whereas the reference rejected each as usage
errors (exit 64). The reference's digit-only parser is the clearer interpretation of the CLI's
"positive decimal integer" contract.

This is learner-visible scaffold code that is likely to be retained. Use one shared digit-only
rule and add CLI cases for whitespace, signs, overflow, zero, missing values, and extra arguments.

## 5. Low — polish two learner-facing boundaries

- `starter/README.md:20` points to "requirement 6.6", but there is no section 6.6; it appears to
  mean milestone 6 in `REQUIREMENTS.md:126-130`.
- `LICENSE_BOUNDARY.md` correctly keeps the linked resource at `NOASSERTION` and explicitly grants
  no upstream rights. It describes generated material only as being on a "personal educational
  use basis", not under a named license or precise permission grant. If learners may copy, modify,
  or export the starter, state those generated-material permissions explicitly without changing
  the upstream boundary.

## Evidence that held up

- A writable review copy reproduced both supplied strict Makefile builds. The reference passed all
  6 public and 25 sealed cases, and the nested interpreter printed `42`. The incomplete starter
  independently reproduced the documented 0/6 result.
- An independent semantic matrix confirmed uninitialized and implicit zero, left-to-right effects,
  short-circuiting, signed division/remainder, boolean normalization, and ignored `main` return;
  a division-by-zero case also reported the correct source line and exit 70.
- Exact-capacity probes passed for source bytes, bytecode, functions, parameters, locals,
  identifier length, operand values, and active frames. Tested one-over cases failed with bounded
  diagnostics. The deep-parser crash is the material exception.
- Progressive disclosure is structurally sound: reference code, answer keys, private tests, and
  production notes are all under `sealed/`; learner-visible C is only the marked incomplete
  starter. Actual learner-view export/filtering was not available, so TRANSFER_VERIFIED remains
  unproven.
- Manifest and provenance identifiers agree internally. No special files or common credential/key
  signatures were found. The linked source was deliberately not accessed, so independent
  verification of non-copying and upstream licensing remains out of scope.
- Validation claims are notably honest. `MANIFEST.yaml` remains `GENERATED` + `PARTIAL`, requires
  independent validation, and says `productionized: false`; the README and validation record do
  not claim BUILDS, TESTED, FUZZED, BENCHMARKED, REVIEWED, TRANSFER_VERIFIED, or PRODUCTIONIZED.

No completion label is promoted by this review. Re-review should at minimum reproduce the
deep-nesting case under bounded process-tree control after the parser and runner fixes.
