# Independent review

Verdict: **REVISE**.

The core challenge contract, learner progression, and sealed reference are credible on the tested
host. The reference passed the submitted suites and a separate 627-case requirements-based oracle,
and the candidate is appropriately candid about retaining only `GENERATED` and `PARTIAL` labels.
Release should nevertheless wait for the two priority-one issues below.

## Prioritized findings

### P1 — The benchmark harness cannot produce its advertised measurement

`sealed/benchmarks/benchmark.py:18` and `:27` call `time.perf_counter_ns`, but the declared and
observed interpreter is Python 3.6.8 (`VALIDATION.md:24` in the candidate). Running the harness
raises `AttributeError` before the executable starts. There is a second independent defect:
`benchmark.py:12` defaults to 10,000 operations, and `:17` consequently constructs 40,003 input
bytes. R3 accepts at most 4,095 bytes, so even on a newer Python this default workload reaches only
the input-too-large path. The submitted README calls this a reproducible harness, although it is
clearly and correctly labeled as unvalidated and no `BENCHMARKED` claim is made.

Use a timer supported by the minimum Python version (or declare and enforce a newer minimum), keep
the generated program within the contract (at most 1,023 repetitions for this encoding), and make
the smoke check require the expected output before treating the harness as usable.

### P1 — Progressive disclosure is described, not deterministically enforced or evidenced

`AGENTS.md:3-6` names a learner allowlist and tells the learner not to inspect other paths, while the
same submitted tree contains a complete reference, hidden tests, design answers, and exercise
answers under `sealed/`. Those files are readable (`0444`) in this workspace. A prose instruction to
a probabilistic worker is not an isolation boundary. If this tree is delivered as-is, the learner
can read or copy the solution and evaluator cases. If the factory performs an out-of-band filtered
transfer, that mechanism and its result are absent here, so progressive disclosure and transfer
remain unverified.

Keep evaluator material outside the student artifact, or provide a deterministic allowlist-based
export plus a validator-owned check and digest proving that no sealed path is present in the student
view.

### P2 — Harness subprocesses do not satisfy the process-group invariant

`public_tests/test_stackvm.py:15-21,33-40`,
`sealed/reference_tests/test_reference.py:14-20,31-38,148-159`, and
`sealed/benchmarks/benchmark.py:19-26` use argv arrays, timeouts, and captured streams, but none starts
a separate process group or kills that group on timeout. In particular, timing out `make` can leave
assembler/linker descendants, and the short-read `Popen` path leaves the child running if
`communicate` times out.

Centralize bounded process execution, create a new session/process group, and terminate then reap
the entire group on timeout while preserving captured logs.

### P2 — The claimed short-read exercise is nondeterministic

`sealed/reference_tests/test_reference.py:147-159` performs several pipe writes and flushes them
without observing the child's reads. A pipe may coalesce those bytes before the child runs, so the
test can pass after only one data-bearing read. Candidate `VALIDATION.md:97-99` therefore states
more than the test deterministically establishes. Static inspection shows a read loop, and a
reviewer feed with delayed single-byte writes succeeded, but ptrace restrictions prevented tracing
the actual read boundaries.

Use validator-controlled syscall tracing/interception or a synchronized input fixture that proves
multiple short reads before claiming this boundary was exercised.

### P3 — Output-write failure has no coherent contract status

R10 says status 9 protects against an impossible bytecode opcode (`REQUIREMENTS.md:75-79`), while
`sealed/reference/stackvm.S:420-424` maps a failed standard-output write to that same "internal
bytecode error". Closing stdout produced status 9 and that diagnostic. The sealed self-review
honestly discloses this behavior, so this is a contract gap rather than a hidden claim, but learners
cannot infer the intended response to an output failure.

Define output-failure semantics (including `EINTR` and partial diagnostic writes) and align the
reference and tests, or explicitly exclude faulting output descriptors from the educational
contract.

### P3 — Generated-material permissions remain unspecified

The provenance record consistently separates the CC0 catalog from the linked resource marked
`NOASSERTION`, and no copied-content claim was promoted to independent fact. However,
`LICENSE_BOUNDARY.md:7-8` says the pack was generated "for personal educational use" without giving
the generated pack an explicit license or permission grant. That describes purpose and provenance,
not redistribution terms. Add an SPDX license or an explicit rights statement for the generated
material. External comparison with the catalog and linked resource was unavailable here.

## What held up under review

- The starter is intentionally incomplete, builds, and reproduces its documented 8-failure/2-pass
  public baseline rather than pretending to be a solution.
- The reference passed 10 public and 11 sealed test methods, plus 627 reviewer-authored differential
  cases with zero mismatches.
- Two clean builds were byte-identical on this host. ELF inspection confirmed a static, syscall-only
  shape with no dynamic section, undefined symbols, RWX segment, or executable stack.
- Manifest/provenance identifiers and snapshot binding are internally consistent. The upstream
  license uncertainty is stated conservatively, validation labels are honest, and no credential
  pattern, symlink, or special file was found.
- README, requirements, concepts, design questions, starter, tests, sealed design review, debugging
  exercise, and alternatives form a useful conceptual progression once the access boundary is made
  real.

