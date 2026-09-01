# Independent Examiner Rubric: Authorization-Boundary Kickoff

## Scope and evidence boundary

Evaluate only the bounded, manager-authored kickoff for `course_0c0beb8e3224cbbc66b740fe95689163`. A passing result is not evidence of completing an official MIT lab, MIT 6.858, production hardening, or transfer to another system.

The staged learner evidence consists of `SUBMISSION.md`, `NOTES.md`, and `DEBUGGING_LOG.md`. The implementation tree is not staged for the examiner. Do not imply that you executed code or independently verified hashes. Learner-captured output is supporting evidence, not a harness result. Award correctness points only when claims are supported by inspectable code/test excerpts, a consistent decision table, precise commands and outcomes, or reasoning that you can independently check from the staged files. Resolve contradictions in favor of the weaker supported claim.

Do not use the network, seek missing course materials, inspect other workspaces, or edit the submission. Cite file sections or distinctive excerpts in evaluation evidence.

## Contract oracle

The component accepts a principal (`subject_id`, `tenant_id`, one role), an action, and resource metadata (`resource_id`, `tenant_id`, `owner_id`). Roles are `member`, `auditor`, and `admin`; actions are `read`, `write`, and `delete`.

For structurally valid data, the expected policy is:

1. A tenant mismatch always denies with `deny_cross_tenant`, including for an admin.
2. A same-tenant admin may perform every supported action with `allow_admin`.
3. A same-tenant auditor may read any resource with `allow_auditor_read`; write and delete deny with `deny_insufficient_privilege`.
4. A same-tenant member may read or write only an owned resource with `allow_owner`; delete and every action on another owner's resource deny with `deny_insufficient_privilege`.
5. No other valid case allows access.

The CLI accepts exactly one UTF-8 JSON object of at most 4,096 bytes. Trailing JSON whitespace is permitted; trailing non-whitespace and duplicate keys at any depth are not. Objects must have exactly the specified keys. Values must be JSON strings; identifiers must match `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`; roles and actions must be members of their finite sets.

A valid policy decision is exactly `{"allowed":<boolean>,"reason":<code>}` plus a newline and exits 0, including on denial. Every malformed input returns exactly `{"error":"invalid_input"}` plus a newline and exits 2. It must not leak raw input or identifiers or emit an uncaught traceback. Parsing/validation must be separated from the deterministic policy core. Only the Python standard library is needed; the solution has no network, persistence, real secrets, or live target.

## Integrity and safety gates

Apply these before interpreting the numeric score:

- Assign `FAIL` if the evidence shows use of real credentials, probing of a live target, unauthorized/restricted material, examiner material, or another learner's work.
- Assign `FAIL` if the learner fabricates independent validation, materially falsifies observed results, or submits no identifiable implementation-and-test evidence. Ordinary mistakes or honestly labeled incomplete work are not fabrication.
- Cap the result at `REVISE` if policy or test code is claimed but no relevant excerpt is available for inspection, if captured command outcomes are omitted, or if the learner claims official-lab, production-security, transfer, or whole-course completion.
- A hash proves only that the learner reported a string; it does not prove the examiner saw or ran the hashed file.

## Scoring

Score each dimension from the staged evidence. Do not award the same evidence twice merely because it is repeated.

### 1. Evidence discipline and scope — 8 points

- 2: source/test inventory and SHA-256 entries are specific and internally consistent.
- 2: exact commands, exit statuses, captured output/error, and discovered test count are reported.
- 2: learner-captured versus independently verified evidence is labeled honestly; missing or failed checks are visible.
- 2: claims remain within this toy kickoff and explicitly exclude official-course and production completion.

### 2. Threat model and security reasoning — 14 points

- 2: protected assets and security properties include tenant isolation and unauthorized mutation.
- 2: relevant actors and at least four concrete abuse or misuse cases are described.
- 4: trust boundaries and provenance assumptions distinguish authenticated principal data, trusted resource metadata, untrusted requested action, and the all-input-is-simulated CLI.
- 2: fail-open/fail-closed behavior is explicit.
- 2: time-of-check/time-of-use and diagnostic/privacy risks receive technically sound treatment.
- 2: authentication, storage, distributed state, deployment, and other non-goals are not quietly claimed as solved.

### 3. Architecture and contract translation — 10 points

- 3: an inspectable deterministic policy entry point has clear inputs and a decision output.
- 3: strict parsing and schema validation are separated from policy evaluation.
- 2: domain values and reason codes are finite, unambiguous, and used consistently.
- 2: layout, imports, and documented commands are plausible with Python 3 and the standard library.

### 4. Authorization correctness — 24 points

- 6: tenant mismatch dominates every role/action/ownership combination and uses the correct reason.
- 4: same-tenant admin behavior is correct for all three actions.
- 4: same-tenant auditor read versus mutation behavior is correct and ownership-independent.
- 5: same-tenant member ownership, read/write, and delete behavior is correct.
- 3: remaining valid cases fail closed and rule/reason precedence is deterministic.
- 2: external decision objects contain exactly the required Boolean and reason code.

Do not infer these points from “all tests pass.” Check the policy excerpt, decision table, and test evidence against the oracle.

### 5. Strict boundary and failure behavior — 15 points

- 3: UTF-8, one-object parsing, the 4,096-byte limit, and trailing-data handling are evidenced.
- 3: duplicate keys are rejected at every object depth rather than silently overwritten.
- 4: exact keys, JSON string types, identifier grammar, and role/action enums are enforced.
- 3: allow, policy deny, and malformed input have the required output shapes and exit statuses.
- 2: malformed paths use one generic response and do not expose raw data, identifiers, or tracebacks.

### 6. Test design — 18 points

- 5: the full 3 × 3 × 2 × 2 role/action/ownership/tenancy space is generated or enumerated, with meaningful assertions.
- 3: reason codes and cross-tenant precedence are explicitly tested.
- 4: deterministic invariant tests cover tenant isolation, auditor non-mutation, and member ownership limits without merely calling the implementation to calculate expected values.
- 4: malformed cases cover empty/invalid/non-UTF-8/duplicate input, missing/extra keys, wrong types, bad identifiers, unknown enums, trailing data, and oversize input.
- 2: subprocess checks use an argument array, bounded timeout, captured streams, and assert both response and status.

### 7. Engineering judgment and maintainability — 7 points

- 2: code excerpts show small responsibilities, readable names, and deterministic behavior.
- 2: diagnostics and reason codes balance operational usefulness with data minimization.
- 2: evidence is reproducible and traceable from command to file/test excerpt.
- 1: limitations and unfinished work are concrete rather than boilerplate.

### 8. Debugging and comprehension — 4 points

- 2: at least three genuine entries connect hypothesis, exact experiment, observation, and conclusion; they are not a reconstructed success narrative.
- 2: comprehension responses address trust authenticity, finite-case limits, parser/policy separation, duplicate-key ambiguity, TOCTOU, role extension, dependency failure, and claim boundaries without major misconceptions.

Total: 100 points.

## Verdict

- `PASS`: 80–100, no integrity/safety gate, at least 20/24 for authorization correctness, 11/15 for strict boundary behavior, and 13/18 for test design.
- `REVISE`: 55–79, or a score of 80+ that misses a critical category minimum or triggers a revise cap.
- `FAIL`: 0–54 or a fail gate.

Use the earned numeric score even when a cap changes the result. In `evaluation.json`, emit exactly `result`, `score`, `evidence`, and `transfer_gaps`; `result` is `PASS`, `REVISE`, or `FAIL`, and `score` is from 0 through 100. Evidence entries must identify what in the staged files supports the judgment. Transfer gaps must include unverified execution and unstaged implementation limitations where applicable; they must not claim full-course assessment.

In `feedback.md`, lead with the verdict, separate observed evidence from learner claims, name the highest-impact correction, and give bounded next steps. Do not reveal this scoring document verbatim or add answers to learner materials.
