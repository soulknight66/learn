# Independent examination

**Result: PASS — 99/100.** No critical cap applies. This result covers only the locally authored retry-safe CourierKV kickoff; it is not official course credit or evidence of a production implementation.

| Dimension | Score | Examiner finding |
|---|---:|---|
| Correctness | 35/35 | The failure model, compound identity, state, transitions, invariants, T1-T4, B1, and C1-C7 are mutually consistent. |
| Evidence | 24/25 | The traces and nine proposed tests are replayable and candidly labeled as desk work. Minor property-specification and cross-reference defects cost one point. |
| Engineering judgment | 25/25 | Contract ownership, retention/recovery limits, deterministic implementation boundaries, operability, and production gaps are handled with appropriate scope. |
| Debugging practice | 15/15 | Four complete cycles preserve failed hypotheses, counterexamples, revisions, reruns, and remaining uncertainty. |
| **Total** | **99/100** | **PASS** |

## What the evidence establishes

Independent execution of the stated transition rules reproduced every required trace result:

- T1 records A1 before losing its reply, so the retry returns cached `OK`, leaves `x="r"`, and keeps the application count at one.
- T2 retains A1 after A2, so the delayed `Put` cannot roll `x="red+blue"` back.
- T3 records `VALUE("red")` for B1 and replays it after the current value becomes `"green"`.
- T4 returns `ID_CONFLICT` for A7's changed body without replacing its `v1` record or mutating the map.
- B1 loses both volatile structures at restart, classifies the retry as first-seen, and reaches two cross-incarnation applications. It does not smuggle persistence into the base model.

V2, V6, and V9 were also replayed independently: reply loss does not duplicate an append, operation/key/argument changes all conflict without state changes, and a cached `NOT_FOUND` remains historical after another client creates the key. Small duplicate, conflict, cross-client, and present-empty sequences satisfy the bounded property's intended valid-request interpretation.

The final design has no material retry-safety misconception. The three incorrect designs in debugging cycles 1-3 are clearly retained as failed hypotheses, not presented as final behavior.

## Corrections to make

1. In the property at `SUBMISSION.md` lines 318-323, quantify over **valid, successfully canonicalized** different bodies. As written, “all different-body deliveries” can include malformed reuse, but validation runs first and correctly returns `INVALID_REQUEST`, not `ID_CONFLICT`. Fix the generator bound to an unequivocal value such as `max_length = 5` instead of “such as 5.”
2. Repair the evidence links in `NOTES.md`: line 16 cites nonexistent `G7`, and line 20 cites T4 for equal-sequence cross-client isolation even though the direct evidence is V5 and debugging cycle 3.
3. Tighten B1's blanket statement that G1-G5 lose their premise. Lost history removes the cross-incarnation basis for G1, G2, and G4; deterministic handling (G3) and pair-key separation (G5) still operate within the new incarnation.
4. Make client handling of `ID_CONFLICT` explicit: treat it as a terminal protocol violation for that call, not a response that retry policy can resolve.

## Recommended next artifact

Build a pure transition harness first and encode V1-V9 as deterministic unit tests, including independent per-ID application counters and reply-loss as data. Then run a finite exhaustive explorer with a fixed request alphabet and fixed maximum sequence length, checking all three properties after every prefix.

After that, address transfer in this order: crash-atomic durable state and recovery tests; authenticated sessions plus safe history collection; protocol size/encoding and concurrency/overload behavior; and only then replica ordering, fencing, and failover. Keep the proposed logging and metrics labeled unvalidated until privacy, capacity, and runtime behavior are measured.
