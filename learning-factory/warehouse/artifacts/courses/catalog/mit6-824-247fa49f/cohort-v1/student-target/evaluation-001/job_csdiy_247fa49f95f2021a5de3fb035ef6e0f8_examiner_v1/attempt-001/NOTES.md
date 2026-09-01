# CourierKV kickoff notes

## Scope and evidence status

These notes cover only the locally authored retry-safety kickoff. I used only
`COURSE_BRIEF.md`, `STUDY_TASK.md`, and `COMPREHENSION.md`. The trace results are
manual, deterministic desk checks of the transition table in `submission.md`.
The tests there are proposed tests, not executed software tests.

## Assumption ledger

| Assumption | Source | Consequence if false | Boundary documentation |
|---|---|---|---|
| There is one server and it does not crash in the base model. | Given | Volatile map and history can disappear, so retries may be applied again. | `submission.md`: G1--G6 boundaries and B1 |
| One delivered request is processed atomically at a time. | Given | Two first deliveries of one ID could both miss history and both mutate the map. | State-transition atomicity and implementation note |
| The network can lose, duplicate, delay, and reorder attempts and replies, but cannot corrupt or forge them. | Given | Corruption requires authentication/integrity rules; forgery can defeat client identity. | Vocabulary, G7, and production gaps |
| Eventual delivery is not guaranteed, and clocks have no correctness role. | Given | There is no unconditional completion guarantee; a timeout cannot identify remote state. | Timeout contract, G6, C1, and V1 |
| `client_id` is nonempty and stable; `seq` is positive and increases within a conforming client session. | Given | Reuse can alias unrelated operations; the server can only detect different retained bodies, not the caller's intent. | Request vocabulary, G5, and C2 |
| A conforming client has at most one logical request outstanding and retries an exact copy. | Given | Multiple bodies with one ID are rejected, but pipelined sequencing and client recovery semantics remain unspecified. | Request vocabulary, conflict rule, and ownership |
| Request identity is the pair `(client_id, seq)`, not `seq` alone. | Given | Using only `seq` causes false conflicts across clients. | I4, T4, V5, and debugging cycle 3 |
| Empty keys and empty values/suffixes are valid finite strings. | Chosen | An implementation that rejects empty keys would have a different protocol and different malformed-input results. | Vocabulary and operation postconditions |
| String comparison is exact over a canonical, length-delimited representation. | Chosen | Ambiguous concatenation or normalization could mistake a conflict for an exact retry. | Fingerprint definition and I2 |
| A malformed request is rejected without creating history. | Chosen | Malformed-attempt deduplication is not durable or stateful; validator-version changes could change its reason code. | Malformed-input rule and V9 |
| A first-seen valid body, including a `Get`, and its semantic response are retained without eviction for the process lifetime. | Chosen | Eviction would make an arbitrarily delayed attempt look new and could change a read response or repeat a mutation. | Retention policy, I2--I3, T2--T3, and C4 |
| The model stores the canonical body, rather than relying on a finite hash. | Chosen | Replacing it with a digest adds a collision assumption and may make equality probabilistic. | Logical state and production gap 3 |
| Response stability means the same response variant and payload, not identical transport bytes. | Chosen | Byte-for-byte retransmission would additionally require fixed serialization/version metadata. | Response vocabulary and I3 |
| All strings are finite, but the packet supplies no size limits or traffic rate. | Given absence / explicitly preserved uncertainty | Memory capacity and handler termination cannot receive a numeric worst-case bound. | Complexity, capacity estimate, and unresolved questions |

## Alternatives considered

| Alternative | Attraction | Discriminating result | Decision |
|---|---|---|---|
| Remember only the latest request per client. | `O(C)` entries instead of `O(N)`. | In T2, accepting A2 and forgetting A1 lets the delayed A1 execute again and overwrite `red+blue` with `red`. | Rejected; retain every accepted request for this incarnation. |
| Remember request bodies but recompute responses. | Avoids caching possibly large `VALUE` results. | In T3, the repeated B1 read would return `green`, not its original `red`. | Rejected; cache the semantic response for every operation. |
| Use `seq` alone as the history key. | Smaller-looking identifier. | A1 and B1 are distinct requests despite sharing sequence 1; sequence-only identity falsely aliases them. | Rejected; use `(client_id, seq)`. |
| Treat a changed body under an old ID as a new request. | Permissive client behavior. | T4 would silently apply `v2` and destroy the meaning of retry identity. | Rejected; return `ID_CONFLICT` without changing map or history. |
| Retain only a hash of the body. | Fixed-size records. | Equality then depends on collision resistance, which the logical exercise does not provide. | Keep the canonical body in the model; revisit authenticated digests for production. |
| Evict by wall-clock age. | Bounds memory simply. | Allowed message delay has no correctness-related time bound, so an old delivery can arrive after eviction. | Rejected in the base design; a future session/acknowledgment protocol is needed. |
| Promise success after timeout if retries are enabled. | Convenient API. | Request loss and reply loss are observationally indistinguishable at the deadline. | Rejected; return `UNRESOLVED_TIMEOUT`. |

## Claim-to-evidence index

| Claim | Preserved evidence | Status |
|---|---|---|
| An accepted mutation is applied at most once in one retained, noncrashing incarnation. | I1/I7; T1.1--T1.2; T2.1--T2.3; proposed V2/V3; debugging cycles 1 and 4 | Desk-checked for named traces; broader test unexecuted |
| Exact retries receive the original semantic response. | I3; T1.2; T3.2--T3.4; proposed V2/V4 | Desk-checked for named traces |
| Delayed old attempts cannot roll state backward while their records remain. | T2.3; proposed V3; debugging cycle 1 | Counterexample found for one-entry policy; revised design desk-checked |
| Equal sequence numbers from different clients remain independent. | I4; proposed V5; debugging cycle 3 | Desk-checked |
| A different body under a retained ID cannot silently execute. | I2/I6; T4.2; proposed V6 | Desk-checked |
| The transition is deterministic for a supplied ordered event stream. | I5; proposed V7 and bounded property generator | Specified, not software-tested or proved |
| A timeout reveals no unique remote outcome. | Timeout contract; proposed V1; C1 | Established by two concrete compatible histories, not a running-network experiment |
| Volatile restart breaks the base retry-safety argument. | B1; proposed V8; debugging cycle 4 | Boundary desk-check completed; no persistence experiment |

## Open questions and deliberately unperformed work

- What byte encoding, normalization rule, and maximum sizes should apply to IDs,
  keys, values, suffixes, and cached responses?
- How is a stable client identity authenticated, and how is sequence reuse
  prevented after client data loss?
- What acknowledgment or session-expiry protocol could make history collection
  safe despite delayed attempts?
- Which durable store could atomically commit a key/value mutation and its
  deduplication response, and what crash faults does it actually tolerate?
- What ordering, leader, quorum, membership, and fencing rules would a
  replicated service require?
- How would concurrent parsing, cancellation, overload, and shutdown interact
  with the state-owner boundary?
- No Go implementation, executable unit test, exhaustive generator, race test,
  crash-injection test, network experiment, benchmark, or operational dashboard
  was produced or run.

## Lessons retained

- A retry is another attempt for an existing logical operation, not a new
  operation merely because it arrives later.
- Caching only mutation outcomes is insufficient: a read result is part of the
  observable history of its request ID.
- A timeout is useful evidence about a local deadline, but not evidence of
  remote non-execution.
- Deduplication retention is a protocol question, not just a cache-tuning
  question.
- Deterministic trace evidence can refute a design quickly, while still falling
  short of proof or production validation.
