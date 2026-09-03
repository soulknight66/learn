# Independent review

Verdict: **REVISE**

The pack has a strong educational shape and unusually candid status boundaries, but the sealed oracle does not yet satisfy its own contract. Two independently reproduced P1 defects block an advisory pass. Publication also needs an orchestrator-captured student-view isolation check; this review cannot confer `REVIEWED`.

## Prioritized findings

### P1 — Valid, in-contract syntax can overflow the host parser stack

`REQUIREMENTS.md:9-10` accepts ASCII sources through 1,048,576 bytes, its grammar permits nested parenthesized expressions, and no parser-depth ceiling is documented. `sealed/reference/src/compiler.c:184-186` recursively re-enters the full precedence ladder for every parenthesis; unary expressions and nested statements are recursive too.

An independently generated, valid 16,021-byte program containing 8,000 nested parentheses aborted with status `-11` under the normal build. The same case under ASan aborted with status `-6` and reported:

```text
AddressSanitizer: stack-overflow
```

This is neither acceptance nor a deterministic compile-time diagnostic and makes the sealed implementation unsafe as an oracle. Add a checked nesting limit to the language contract and compiler, or make parsing iterative. Add normal and sanitizer regressions at and beyond the chosen boundary for parentheses, unary chains, nested blocks, and nested control-flow statements.

### P1 — Runtime diagnostics violate the learner-facing prefix contract

`REQUIREMENTS.md:128-131` requires user errors to begin `path:line:column:`. Compile diagnostics do. Runtime diagnostics do not: `sealed/reference/src/vm.c:42-44` formats `runtime error: ... (line N, column N)` and the VM has no source path.

Observed on the submitted overflow fixture:

```text
rc=1
stderr=runtime error: signed arithmetic overflow (line 3, column 19)
```

The public test at `public_tests/test_public.py:82-85` only searches for `runtime error:`, so it codifies the implementation rather than the stated contract. Carry the source path through execution (or return structured location data), emit `path:line:column: runtime error: ...`, and assert the exact stable prefix for every runtime-error class.

### P1 release gate — Sealed disclosure is described, not enforced by this artifact

The reveal order is clear, and the learner-facing trees contain no textual references to the sealed implementation. However, `sealed/` is a world-readable subtree beside `starter/`; `AGENTS.md` only asks learners not to read it. `sealed/reference_tests/verify_pack.py:15-39` requires sealed paths in the pack but does not construct or validate a learner projection.

This reviewer workspace is expected to expose sealed content, so its presence is not itself proof of a leak. It does mean publication must be conditional on an external, deterministic validator proving that the actual student view excludes all of `sealed/`, hidden tests, answers, and reference artifacts. Prose instructions and Unix read-only bits are not isolation.

### P2 — Zero-budget behavior is ambiguous between the contract and oracle

The required CLI is documented as `--max-steps N` without a lower bound (`REQUIREMENTS.md:117-126`), and the learner adversarial exercise explicitly requests a zero-budget case (`adversarial/README.md:17`). The oracle instead labels the value positive and rejects zero in `sealed/reference/src/main.c:92-105`.

Observed:

```text
rc=2
invalid positive instruction budget: 0
```

Either accept zero and let execution fail before dispatching an instruction, matching the VM API, or state the positive-only rule in the normative requirements and define zero as a usage-error oracle. Add the corresponding public or sealed test.

### P2 — Validation language is broader than the durable tests

`VALIDATION.md:56-59` and `sealed/adversarial/README.md:3-6` say the private suite covers arithmetic and requested adversarial boundaries. The submitted tests sample normal operators, `INT64_MAX + 1`, and `INT64_MIN / -1`, but omit durable checks for subtraction, multiplication, unary-negation and remainder overflow, division/remainder by zero, zero budget, exact runtime prefixes, and syntax-depth exhaustion. The direct VM suite has only nine failure programs.

The implementation passed 23 independent reviewer-generated boundary cases, which is useful evidence but is not durable candidate coverage. Add deterministic tests for these cases and narrow prose claims to the exact exercised set. The explicit statements that no fuzzing or benchmark was performed are honest and should remain.

## Other observations

- Functional reproduction was good: strict normal and sanitizer builds, all submitted suites, archive verification, and the finite tower passed independently.
- Binary reproduction is not path-independent. Identical clean builds in two directories produced SHA-256 values `d19e328a...` and `517301cf...`; GNU `strings` showed each absolute build directory embedded by `-g`. No reproducible-binary label is claimed, but use debug/file prefix maps and expected artifact hashes if that becomes a goal.
- Progressive disclosure in the prose is good, but learner feedback is front-loaded: the only staged public milestone has two lexer checks, followed by seven skips until compiler and VM completion. Small parser, emitter, and direct-VM milestone tests would make the challenge more useful without revealing the sealed oracle.
- The starter interface lacks the reference's local-count and source-location metadata. Learners may change it, but the starter guide should explicitly call out that this redesign is necessary to implement safe local validation and the required runtime diagnostics.

## License and provenance assessment

The pack distinguishes the CC0 catalog metadata from the linked tutorial's `NOASSERTION` status, says the link is not permission, and makes no broad upstream-license claim. `MANIFEST.yaml` and `PROVENANCE.json` agree on project, source, commit, and snapshot identifiers; the provenance file's independently computed SHA-256 matches the verifier's pinned value. A full-tree scan found 61 regular files, no symlinks or special entries, and no credential-pattern hits.

The immutable source snapshot and network were unavailable, so the upstream commit, baseline hashes, linked-resource license, and independent-authorship statement remain externally unverifiable. The generated material also carries no redistribution license; `LICENSE_BOUNDARY.md` appropriately tells redistributors to perform their own rights review.

## Acceptance conditions

1. Prevent or deterministically diagnose parser-depth exhaustion and add boundary regressions.
2. Make all runtime diagnostics obey the normative `path:line:column:` prefix and test them.
3. Resolve and test the zero-budget contract.
4. Add the missing durable boundary coverage and correct validation-scope wording.
5. Require an orchestrator-captured student-view isolation validator before release.

Only an independent acceptance validator may publish `REVIEWED`; this verdict is advisory.
