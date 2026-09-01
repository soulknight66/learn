# CourierKV debugging log

All observations below are desk executions of the stated candidate table or the
final transition pseudocode. They are not outputs from an implementation.

## Cycle 1 — one retained record per client

Cycle: 1  
Hypothesis: Because a conforming client issues increasing sequence numbers, retaining only its latest full request record is sufficient for duplicate suppression.  
Exact initial state and event stream: Candidate state is `M={}`, `latest={}`. Deliver `Put(A,1,"x","red")`; deliver `Append(A,2,"x","+blue")`; then deliver a delayed duplicate `Put(A,1,"x","red")`. Deliver every reply. The candidate replaces `latest[A]` on each first-seen ID and treats an ID different from that slot as first-seen.  
Predicted observation: Responses `[OK, OK, OK]`, final `M={x:"red+blue"}`, and one application of A1.  
Observed result from executing the current table or pseudocode: After A2, the only slot is `(A,2)`. The delayed A1 misses that slot, is classified first-seen, and executes `Put` again. Responses are `[OK, OK, OK]`, but final `M={x:"red"}` and A1 has two applications.  
Discrepancy or confirmation: Counterexample. Increasing issue order does not imply delivery order, and the response sequence alone hides the rollback.  
Design/test revision: Replace the per-client latest slot with immutable history for every first-seen valid `(client_id,seq)` for the entire server incarnation. Add delayed-old-attempt test V3 and assert both final map and per-ID application count.  
Rerun result: With both A1 and A2 retained, the third event reads A1's record, returns its cached `OK`, performs no write, and leaves `M={x:"red+blue"}`; A1's application count remains 1.  
Remaining uncertainty: Safe garbage collection still needs an acknowledgment, session, or bounded-delay assumption not present in the packet.

## Cycle 2 — recomputing duplicate reads

Cycle: 2  
Hypothesis: Retaining a request fingerprint is sufficient; an exact duplicate `Get` can be evaluated again because reads do not mutate the map.  
Exact initial state and event stream: Candidate state starts `M={}`, `H={}` and records bodies but not read responses. Deliver `Put(A,1,"x","red")`, `Get(B,1,"x")`, `Put(A,2,"x","green")`, and a duplicate `Get(B,1,"x")`; deliver all replies.  
Predicted observation: The two B1 attempts are one logical read and should both yield `VALUE("red")`; final `M={x:"green"}`.  
Observed result from executing the current table or pseudocode: The first B1 delivery yields `VALUE("red")`. After A2, reevaluating B1 against the current map yields `VALUE("green")`. The map remains `{x:"green"}`, but the same logical request has two semantic responses.  
Discrepancy or confirmation: Counterexample to response stability I3; lack of mutation does not make a repeated evaluation the same observation.  
Design/test revision: Store the chosen semantic response in every history record, including `VALUE` payloads and `NOT_FOUND`. Exact retries return that response without consulting the current map. Add V4.  
Rerun result: T3.4 reads B1's cached `VALUE("red")`; it returns `red` while the map remains `{x:"green"}`.  
Remaining uncertainty: Cached values can make history large and sensitive; size limits and protected storage are unspecified.

## Cycle 3 — sequence-only identity

Cycle: 3  
Hypothesis: A positive sequence number can be the history key because every client increases it.  
Exact initial state and event stream: Candidate state is `M={}`, `H_by_seq={}`. Deliver `Append(A,1,"x","a")`, then `Append(B,1,"x","b")`; deliver both replies.  
Predicted observation: The requests are independent, responses are `[OK, OK]`, final `M={x:"ab"}`, and each request is applied once.  
Observed result from executing the current table or pseudocode: Sequence 1 is occupied after A1. B1 has a different body, so the sequence-only table classifies it as `ID_CONFLICT`; responses become `[OK, ID_CONFLICT]` and final `M={x:"a"}`.  
Discrepancy or confirmation: Counterexample. Sequence monotonicity is scoped to a client, not to the service.  
Design/test revision: Key history by the pair `(client_id,seq)` and compare bodies only within that pair. Add cross-client invariant I4 and V5.  
Rerun result: A1 and B1 occupy different records, both return `OK`, and final `M={x:"ab"}` with one application each.  
Remaining uncertainty: The base model assumes stable client IDs; it provides no authentication or recovery rule for them.

## Cycle 4 — volatile restart boundary

Cycle: 4  
Hypothesis: The final in-memory design establishes retry safety only within one uninterrupted incarnation; applying B1 should expose two applications across a restart.  
Exact initial state and event stream: Start incarnation 1 with `M={}`, `H={}`. Deliver `Append(A,1,"x","r")` and lose `OK`; crash after the atomic map/history transition; restart incarnation 2 with the policy-guaranteed empty `M` and `H`; deliver the exact A1 retry and deliver its reply.  
Predicted observation: Incarnation 1 reaches `M={x:"r"}` with A1 recorded, then loses both volatile structures. Incarnation 2 classifies A1 first-seen and applies it. The final map is again `{x:"r"}`, the delivered response is `OK`, and the observed application count across incarnations is 2.  
Observed result from executing the current table or pseudocode: The desk transition produces exactly that sequence. The equal final value does not erase the second application.  
Discrepancy or confirmation: Confirmation of a boundary, not confirmation of crash-safe at-most-once behavior.  
Design/test revision: Keep restart outside the base guarantee, make `server_incarnation` explicit in operational evidence, add V8, and name a future durable transaction that commits both the map mutation and immutable history response atomically.  
Rerun result: Re-running T1 without a crash gives one application and a cached retry response; re-running B1 with volatile restart still gives two applications, as the documented boundary predicts.  
Remaining uncertainty: No durable store, crash injection, recovery validation, or atomicity test was implemented; replication would add ordering and consensus questions.
