# Independent Evaluation Rubric — Authentication Boundary Kickoff

This document is examiner-only. Evaluate the learner's submitted artifacts, not their assertion that the work is complete. This rubric validates only `kickoff_u01_authentication_boundary`; it cannot establish completion of an MIT module, any reported MIT lab, or the course.

## Evaluation protocol

1. Work from a disposable copy and use synthetic credentials only. Do not access a network or a real account.
2. Confirm the five required learner files exist.
3. Run `python3 -m unittest discover -s tests -v` in a clean Python 3 process and retain the exit status and captured output as evidence.
4. Inspect implementation paths independently of the learner's tests.
5. Add or run examiner probes where necessary; do not award behavior points solely because a learner-authored test says it passed.
6. Check that prose statements correspond to identifiable code and tests. Record contradictions as findings.

Score out of 100, then apply the critical caps. A score of 75 or higher, with no critical cap or safety violation, is the recommended unit-pass threshold.

## 1. Reproducible submission — 8 points

- 2: All five required learner files are present at the specified locations.
- 3: The documented test command runs without network access, third-party packages, order dependence, or manual setup.
- 3: The captured run passes and the engineering note reports the same command/result honestly.

## 2. Threat model and scope — 14 points

- 4: Assets, adversary capability, trusted/untrusted inputs, and the local trust boundary are concrete and mutually consistent.
- 4: At least four relevant cases are analyzed, including stolen credential records and user enumeration.
- 3: Controls are mapped to the component instead of vaguely assigned to “security.”
- 3: Deferred controls and the local/synthetic-only boundary are explicit; no production-completeness claim is made.

## 3. Contract and record design — 14 points

- 4: Enrollment, verification, duplicate, unknown-user, wrong-password, and invalid-input behavior form an unambiguous contract.
- 3: Input length, string-to-byte conversion, and Unicode policy are documented and implemented consistently.
- 4: Records contain an explicit version, algorithm, per-record iteration count, salt, and derived verifier, with meaningful validation.
- 3: State is encapsulated without an unsafe public inspection/export interface; any test seam is narrow and justified.

## 4. Credential derivation and secret handling — 20 points

- 5: The code actually calls `hashlib.pbkdf2_hmac` with SHA-256 and does not contain a homemade cryptographic substitute.
- 4: The normal default is at least 600,000 iterations, configuration is validated, and the per-record value is used during verification.
- 4: Each enrollment requests at least 16 fresh random bytes; the production default reaches an operating-system-backed source.
- 4: No plaintext or reversible password appears in stored state, representation output, logs, fixtures, or exception text.
- 3: Derived values are compared through `hmac.compare_digest`.

Examiner probe: inject a deterministic sequence of two salts, enroll two synthetic users with the same password, and inspect through the learner's documented test seam or in a disposable copy. Confirm both records and derived verifiers differ. Separately spy on `pbkdf2_hmac` to confirm the stored record parameters drive verification.

## 5. Verification and failure behavior — 16 points

- 4: A correct password succeeds while a wrong password and unknown user both return `False` through the public API.
- 3: Duplicate enrollment cannot silently replace a valid record.
- 4: The unknown-user path performs one dummy PBKDF2 derivation at the configured cost before returning; the learner does not claim whole-function constant time.
- 3: Malformed records and unsupported versions fail without authenticating, guessing defaults, or leaking credential values.
- 2: Input and configuration errors follow the documented policy without confusing them with authentication success.

Examiner probes: spy on the PBKDF2 call for a nonexistent user, corrupt each required record field in turn, and attempt verification. Do not use elapsed-time thresholds as evidence.

## 6. Test quality — 18 points

- 8: Independent tests cover success, wrong password, unknown user, duplicate enrollment, invalid/boundary inputs, distinct salts, malformed record, unsupported version, dummy derivation, and bad configuration. Award proportionally; nominal test names without meaningful assertions receive no credit.
- 4: Nondeterminism is controlled through a narrow seam while the production default remains secure.
- 3: Tests check an invariant or interaction, not merely line execution; at least one test would fail if ordinary hashing replaced PBKDF2.
- 3: Tests are isolated, deterministic, network-free, and avoid wall-clock timing claims.

## 7. Engineering reasoning and comprehension — 10 points

- 4: The engineering note maps controls to concrete code/tests, discusses two genuine alternatives with tradeoffs, names omissions, and proposes a testable next change.
- 6: Comprehension responses are accurate, concise, specific to the artifact, and cite evidence where requested. Use the indicators below; award partial credit for correct reasoning with weak artifact linkage.

Expected comprehension indicators:

1. The learner distinguishes caller-controlled identifiers/passwords, internal record state, the component boundary, and a deferred surrounding service or storage system.
2. Stolen records permit offline guesses. A unique salt prevents cross-record/precomputed reuse; the iteration count raises per-guess work but does not make weak passwords strong.
3. A direct fast hash makes large guess volumes cheaper. Evidence should constrain the primitive through inspection plus a meaningful interaction or spy test, not digest-value snapshots alone.
4. Constant-time digest comparison reduces content-dependent comparison behavior. It does not equalize lookup/control-flow differences, input handling, system load, KDF parameters, logging, network behavior, or the larger service.
5. Both paths return `False`; dummy work narrows a major difference, but lookup, parsing, allocation, caching, and other effects can remain. A call-count/argument spy is better evidence than a noisy timing assertion.
6. Injected bytes make salt-dependent state repeatable and observable. Production becomes unsafe if deterministic/test entropy is the default or can be selected accidentally outside tests.
7. Malformed or unknown state cannot justify identity, so guessing defaults risks acceptance or downgrade. The cited assertion must demonstrate a false result or documented safe error and no success.
8. Version, algorithm, and per-record work factor enable recognition and policy decisions. Actual migration needs rehash-on-success or reset/upgrade behavior plus backward/forward compatibility and atomic-update tests.
9. Unit tests can justify specific behavior in tested states; they cannot prove absence of all side channels, cryptographic security, production resilience, or system-level security. Appropriate additional evidence may include review, static analysis, benchmarking, penetration testing in an authorized environment, or system threat analysis.

## Critical caps and safety handling

Apply the lowest applicable cap after scoring:

- Maximum 35: plaintext/reversibly encoded passwords are retained or emitted, a homemade password primitive replaces PBKDF2, or real credentials are included.
- Maximum 45: a wrong password or malformed record can authenticate, or verification does not use the stored record's parameters.
- Maximum 50: no executable verifier is submitted.
- Maximum 60: no meaningful executable tests are submitted or the required test command cannot collect them.
- Maximum 70: secure production randomness is absent even if deterministic test entropy exists.
- Maximum 80: the threat model is missing or unrelated to the implementation.

If the submission probes an external service, uses another person's credential/data, or attempts to obtain restricted course material, stop execution, preserve safe evidence, and report the scope violation to the orchestrator rather than investigating further.

## Decision record

Record the raw score, any cap, final score, test command and exit status, examiner probes performed, artifact hashes or locations, concrete findings, and one of `UNIT_PASS_RECOMMENDED` or `UNIT_REVISION_REQUIRED`. The worker harness remains the authority for any durable state transition.
