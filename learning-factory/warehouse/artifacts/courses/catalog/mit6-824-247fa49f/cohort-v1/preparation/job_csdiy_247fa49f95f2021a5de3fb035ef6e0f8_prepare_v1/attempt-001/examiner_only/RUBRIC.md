# Independent Examiner Rubric: Retry-Safe CourierKV Kickoff

## Authority and scope

Evaluate only the learner's `submission.md`, `notes.md`, and
`debugging-log.md` for the locally authored unit
`kickoff_retry_safe_kv_contract_v1`. Do not infer work that is not preserved in
those files, and do not trust a prose completion claim without checkable trace or
experiment evidence.

This is not an MIT lecture, lab, assignment, Raft implementation, or
whole-course assessment. A passing result records success on this bounded
kickoff only.

## Examination procedure

1. Confirm that all three learner files are present and that the final submission
   carries the required local-scope label.
2. Extract the learner's failure model, request identity, state variables,
   transition rules, and invariants before reading their conclusions about the
   traces.
3. Re-execute T1–T4 against those rules. Check every state and response claim for
   consistency, including historical responses and mutation counts.
4. Inspect B1 separately. Ensure the learner does not smuggle crash recovery or
   persistence into the base model.
5. Re-evaluate at least three learner test oracles and the quantified
   property-style statement using small hand-generated event sequences.
6. Check that each cited debugging observation follows from the recorded initial
   state, events, and version of the transition rules. Failed hypotheses must
   remain visible.
7. Cross-check the contract, traces, tests, comprehension responses,
   observability plan, and limitations. Contradictions are evidence against the
   stronger claim.
8. Record concrete file/section evidence for each scored dimension and list
   transfer gaps separately.

Equivalent representations are acceptable. Grade behavior and reasoning, not
pseudocode style. Do not require implementation or execution evidence: this unit
is explicitly a design-and-deterministic-trace exercise.

## Reference correctness anchors

Use these anchors to detect semantic errors while accepting justified equivalent
designs:

- Request identity is the compound pair `(client_id, seq)`; equal sequence
  numbers from different clients must not collide.
- Correct retry classification requires enough retained information to compare
  the request body and reproduce the original response. A history entry normally
  includes a request fingerprint plus the chosen response.
- A first-seen valid mutation updates the map and history as one atomic logical
  transition. An exact duplicate returns the recorded response without another
  map mutation. A conflicting body under an existing ID is rejected or surfaced
  as a protocol violation without changing the map or replacing the original
  history entry.
- A first-seen `Get` records the result selected at that transition. Its exact
  duplicate returns that historical result, even if a later mutation changed the
  current map.
- A local timeout is consistent with, among other histories, loss before server
  delivery and loss of a reply after application. It does not establish success
  or non-application.
- With arbitrary delay, retaining only the latest response for a client cannot
  both forget an older request and later reproduce that older request's response.
  A correct design either retains sufficient history or introduces and clearly
  scopes an additional acknowledgement/session/expiry protocol that is absent
  from the base model.
- Unconditional progress is unavailable because the model permits every attempt
  to be lost. Any liveness statement needs a delivery/retry/fairness assumption.
- Volatile map and history loss at restart destroys the base evidence for
  at-most-once behavior. Preserving the guarantee requires an additional
  mechanism, such as atomic durable update of service state and duplicate
  metadata or a carefully specified session/epoch protocol. This still does not
  solve replica agreement.

Expected trace landmarks:

- **T1:** the append's mutation count is one; the final value of `x` is
  `"r"`; the retry returns the response selected for the original delivery.
- **T2:** the delayed old `Put` does not undo the later append; immediately
  before the final `Get`, `x` is `"red+blue"`; the old attempt receives its
  historical response.
- **T3:** the first `Get(B, 1, "x")` observes `"red"`; its duplicate returns
  that same historical result after the current value becomes `"green"`.
- **T4:** the first request under `(A, 7)` establishes `"v1"`; the conflicting
  request neither writes `"v2"` nor replaces the original history; the final
  `Get` observes `"v1"`.
- **B1:** without added durable or session state, the retry can be classified as
  new after restart and the append may be applied again. The base contract cannot
  claim restart-safe at-most-once behavior.

## Scoring: 100 points

### Correctness — 35 points

- **Failure model and vocabulary (5):** accurately preserves the given delivery,
  atomicity, volatility, and progress boundaries.
- **Identity, transition rules, and invariants (12):** gives consistent handling
  of first-seen, exact duplicate, cross-client, conflicting, read, and missing-key
  cases without silent state changes.
- **Trace execution (12):** T1–T4 maps, histories, responses, mutation counts,
  and invariant citations match the learner's contract and the reference
  landmarks.
- **Comprehension accuracy (6):** C1–C7 use causal reasoning and do not expand
  claims beyond the model.

### Evidence — 25 points

- **Trace evidence (8):** rows contain enough before/after detail for independent
  replay; unchanged fields and lost replies are explicit.
- **Verification plan (8):** at least eight bounded tests have exact event
  streams, oracles, final-state expectations, failure signatures, and invariant
  coverage. The property-style statement is precise and the proposed exploration
  is finite.
- **Traceability (5):** the claim-to-evidence index resolves to actual sections,
  and notes expose assumptions, alternatives, and open risks.
- **Honesty and reproducibility (4):** unperformed checks, timebox status, and
  material-use statement are candid; no invented external result is presented.

### Engineering judgment — 25 points

- **Client contract (6):** response, timeout, ownership, validation, and
  protocol-violation behavior are actionable.
- **Retention and recovery boundaries (7):** metadata growth is analyzed; expiry,
  restart, and atomic persistence tradeoffs are explicit rather than hidden.
- **Implementation and test boundaries (5):** deterministic core, state
  ownership/synchronization, atomicity, and non-timing-based tests are separated
  cleanly.
- **Operability (4):** logs avoid values/secrets, metrics use bounded-cardinality
  labels, and the query/capacity alert answer concrete questions.
- **Transfer judgment (3):** production gaps are sensibly ranked and deterministic
  execution is not confused with replica agreement.

### Debugging practice — 15 points

- **Three reproducible cycles (6):** each contains hypothesis, exact setup,
  prediction, observed table/pseudocode result, revision, rerun, and uncertainty.
- **Counterexample quality (4):** at least one preserved failed design is refuted
  by a minimal, relevant event stream.
- **Evidence-driven revision (3):** the identified discrepancy causes a specific
  contract, state, or test change that remains consistent elsewhere.
- **Record integrity (2):** confirmations are distinguished from failures and the
  log does not rewrite history or cite inaccessible tools/materials.

## Critical defects and score caps

Apply all relevant caps after calculating the dimension score:

- Missing any required learner file, or no usable final contract: maximum 49.
- Reapplying the T1 append on its exact retry, allowing the T2 delayed put to
  overwrite later state, allowing T4's conflicting body to mutate state, or
  treating client sequence numbers as globally unique: maximum 59.
- Returning the current value for T3's duplicate read while also claiming stable
  original responses: maximum 69.
- Claiming that a timeout proves non-application, that this volatile design is
  restart-safe, or that deterministic transitions solve replication/consensus:
  maximum 69.
- No reproducible trace tables or fewer than eight test oracles: maximum 69.
- No debugging counterexample and revision: maximum 74.
- Claiming official assignment, Raft, or whole-course completion, or claiming use
  of material that was not available: maximum 49 and identify the unsupported
  claim in feedback.

A documented alternative may avoid a cap only if it explicitly changes the
contract without violating the task's six required behaviors and then applies
that contract consistently to every trace and test.

## Result mapping

- **PASS:** 75–100, no cap below 75, all required files present, and the evidence
  supports the central retry-safety claims.
- **REVISE:** 50–74, or a correctable central gap/cap prevents PASS.
- **FAIL:** 0–49, the submission is absent or non-evaluable, or its central model
  contradicts the task while claiming success.

The examiner's evaluation must cite concrete evidence, state the score and result,
and list transfer gaps. Neither a score nor PASS changes the course's
`DISCOVERED` catalog status or grants official course credit.
