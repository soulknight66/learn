# Independent review

Advisory verdict: **REVISE**.

The submission is unusually careful about reproducibility, progressive disclosure, and honest
status labeling, but independent probes found trust-boundary failures in supplied learner code and
the sealed reference. `CANDIDATE/` was treated as immutable and was not repaired.

## Prioritized findings

### 1. High — huge numeric timeouts escape the required exception contract

`REQUIREMENTS.md` says every configuration-boundary error must be `ValidationError`. Both
`starter/minictr/spec.py:83-88` and `sealed/reference/minictr/spec.py:78-83` call `float(timeout)`
outside an exception-normalization block. A valid Python integer such as `10**400` raises
`OverflowError` instead of being rejected as a non-finite/out-of-range timeout.

This affects the supplied warm-up as well as the answer. A learner who follows the instruction to
focus on TODO stages can retain a hidden-validation failure they were not expected to introduce.
Catch numeric-conversion failures and raise `ValidationError`; add deterministic starter/public and
sealed regression cases for very large integers.

### 2. Medium — Runner emits non-JSON numeric tokens and launches the helper

`sealed/reference/minictr/runner.py:42-50` uses the standard library JSON defaults. Those defaults
accept `NaN`, `Infinity`, and `-Infinity`; a finite JSON spelling such as `1e1000000` also overflows
to infinity. `json.dumps` then emits `NaN`/`Infinity`, which are not JSON numbers and cannot be
called canonical JSON under R5.

An injected-process probe observed all four inputs reaching `communicate`. Reject non-finite decoded
values before process creation (for example, with strict decode handling plus `allow_nan=False`) and
test that the process factory remains untouched.

### 3. Medium — filesystem validation still leaks raw OS errors

`validate_rootfs` checks `path.is_symlink()` before its guarded `resolve` call in both starter and
reference implementations (`paths.py:13`). On this configured Python, an absolute path containing a
5,000-byte component raised `OSError(36, "File name too long")`, not `ValidationError`. The same
pattern exists in executable validation at `sealed/reference/minictr/planner.py:34`.

Guard every filesystem probe at these configuration boundaries and translate ordinary lookup/stat
failures to `ValidationError`. Add overlong-path regressions for rootfs and unshare paths.

### 4. Medium — the distributable view drops its license/provenance notice

`README.md` says only the generated learner view may be distributed, but the learner allowlist in
`environment/export_views.py:17-27` omits both `LICENSE_BOUNDARY.md` and `PROVENANCE.json`. The
resulting artifact therefore does not tell its recipient that the linked resource is
`NOASSERTION`, that linked content is claimed not to be copied, or that generated material is only
described as supplied for personal educational use with legal review advised before redistribution.

Include a learner-safe license/provenance notice in the allowlist and view manifest, or document and
verify an external notice-delivery mechanism. This material contains no sealed answer content and
does not need to be withheld for progressive disclosure.

## Confirmed strengths

- The source pack stayed byte-identical throughout review: 72 files, 19 directories, no symlinks or
  special entries, and the same independent framed digest before and after testing.
- Status claims are honest. The manifest remains `GENERATED` + `PARTIAL`, independent validation is
  required, and productionization is explicitly denied. Builder validation is clearly labeled as
  builder-side evidence rather than proof.
- Reproducibility is strong for a standard-library exercise. The Python path/version is explicit,
  all 43 Python files parse, reported unit-test counts reproduced, and the benchmark is correctly
  described as exploratory rather than `BENCHMARKED` evidence.
- Progressive disclosure works at the content boundary. The generated learner view contained 27
  payload files under exactly nine allowlisted roots; independent recomputation matched every
  manifest path, size, digest, and directory, and no sealed/evaluator/answer root was present.
- Registry transactions use parameterized SQL and `BEGIN IMMEDIATE`; an independent simultaneous
  claim probe produced exactly one winner. The numbered migration installs a fixed-predicate state
  trigger for the tested version-zero legacy schema.
- The host-dependent claims reproduced: the benign writable-rootfs integration passed, while the
  default read-only setup failed before workload launch with an actionable unsupported result.

## Scope limits

The benign Linux smoke test does not prove containment. Successful read-only execution was not
available on this filesystem, and upstream copying/license claims could not be externally checked
without the immutable source baseline. The candidate already discloses the important production
gaps: filesystem TOCTOU, capabilities/seccomp/cgroups, PID-1 behavior, unbounded output, crash
reconciliation, and cross-host coverage. Those limits are consistent with `PARTIAL`; no validation
label should be promoted from this review.
