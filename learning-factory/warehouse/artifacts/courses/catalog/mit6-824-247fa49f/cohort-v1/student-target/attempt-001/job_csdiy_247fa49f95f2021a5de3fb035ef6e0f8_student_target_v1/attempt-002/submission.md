# Retry-Safe CourierKV design dossier

**Scope:** This submission attempts only the bounded, locally authored kickoff
unit. It is a Markdown design and desk-verification artifact, not an
implementation, an official MIT assignment, or evidence of course completion.

## 1. Client-facing contract

### 1.1 Requests, identities, and responses

A valid request is exactly one of:

```text
Put(client_id, seq, key, value)
Append(client_id, seq, key, suffix)
Get(client_id, seq, key)
```

`client_id` must be a nonempty string and `seq` a positive integer. Strings are
finite and compared exactly. I choose to allow empty keys, values, and suffixes
because the packet does not forbid them. A conforming client increases `seq`
within its stable session, has at most one logical request outstanding, and
resends an exact body on retry. The server does not infer global identity from
`seq`: the request ID, or `rid`, is `(client_id, seq)`.

The canonical body is the unambiguous, length-delimited tuple
`(operation, key, argument-tag, argument)`, where `Get` has a distinguished
`NoArgument` tag. In the logical model this tuple itself is the request
fingerprint; it is not a collision-prone hash.

Server response vocabulary:

- `OK`: the first delivery of a valid `Put` or `Append` was accepted, or an
  exact retry is replaying that accepted response.
- `VALUE(value)`: the value observed by the first delivery of a valid `Get`, or
  that same cached observation on an exact retry.
- `NOT_FOUND`: the key was absent at the first delivery of a valid `Get`, or
  that cached result on an exact retry.
- `ID_CONFLICT`: the `rid` exists but its retained canonical body differs from
  the new, otherwise valid body. This reveals no retained argument or value.
- `INVALID_REQUEST(code)`: the message is not one of the valid shapes, has an
  empty `client_id`, or has nonpositive `seq`. Stable, bounded codes include
  `INVALID_SHAPE`, `EMPTY_CLIENT`, and `NONPOSITIVE_SEQ`. Validation failure
  changes neither map nor history and is not retained.

`LOCAL_TIMEOUT(rid)` is not a server response. The client library reports it to
its caller as `UNRESOLVED_TIMEOUT(rid)`: no matching response arrived before a
local deadline. It does **not** mean rejected, not delivered, not executed, or
rolled back. A later client-owned retry must use the exact same `rid` and body.

A first valid body delivered for an unused `rid` wins. Any later valid body for
that ID is either an exact retry or a conflict. Invalid messages are rejected
before this lookup; repeating the identical malformed bytes obtains the same
validation result only while the protocol validator/version is unchanged.

### 1.2 Operation preconditions and postconditions

The server transition is total: malformed input has the rejection behavior
above. The following postconditions describe a valid, first-seen request in the
base environment.

| Operation | Preconditions for acceptance | Atomic postcondition | Chosen response |
|---|---|---|---|
| `Put(rid,k,v)` | Valid envelope/body; `rid` absent from history | `map[k]` is present with `v`; every other map entry is unchanged; insert immutable `(body, OK)` under `rid` | `OK` |
| `Append(rid,k,s)` | Valid envelope/body; `rid` absent | Let `old` be the present value or `""` if absent; make `map[k]` present with `old+s`; leave other keys unchanged; insert `(body, OK)` | `OK` |
| `Get(rid,k)` | Valid envelope/body; `rid` absent | Map is unchanged; cache `(body, VALUE(v))` if `k` is present with `v`, otherwise `(body, NOT_FOUND)` | `VALUE(v)` or `NOT_FOUND` |

For any valid request whose `rid` is present:

- equal canonical body: return the retained response, with no state change;
- unequal canonical body: return `ID_CONFLICT`, with no state change.

These rules do not require consecutive delivery order. In particular, the
server accepts a previously unseen A7 without seeing A1--A6 and recognizes a
retained A1 after A2; conformance of issue order belongs to the client.

### 1.3 Named invariants

- **I1 — At-most-one application.** Within one server incarnation and while its
  record is retained, the map-changing branch is entered at most once for each
  accepted mutation `rid`.
- **I2 — Immutable identity/history.** History has at most one record per
  `(client_id,seq)`. Once inserted, its canonical body and semantic response
  never change. A different body cannot replace it.
- **I3 — Stable semantic response.** Every exact retry of a retained request
  returns the response variant and payload chosen by its first delivery,
  including an old `VALUE` or `NOT_FOUND` result.
- **I4 — Cross-client history isolation.** History lookup and duplicate
  classification use the complete pair `(client_id,seq)`. A sequence used by B
  cannot read, conflict with, or replace A's history record. The application
  map is intentionally shared, so this is identity isolation, not key tenancy.
- **I5 — Deterministic transition.** Equal logical state plus equal delivered
  request produces equal classification, next state, and semantic response.
- **I6 — Nonmutating alternatives.** `Get`, exact retry, `ID_CONFLICT`, and
  `INVALID_REQUEST` do not change the map. Exact retry and conflict also do not
  change history; first-seen `Get` adds only its history record.
- **I7 — Map/history coupling.** For a first-seen mutation, its map update and
  immutable history insertion are one atomic transition. No delivered event can
  observe only one of them in the base model.

### 1.4 Claims, classifications, and boundaries

| ID | Claim or non-claim | Class | Retention / crash boundary | Concurrency boundary | Progress assumption |
|---|---|---|---|---|---|
| G1 | One accepted logical mutation changes the map at most once. | Safety: a second application is a finite bad prefix. | Requires its record for the entire uninterrupted incarnation; not promised across crash/restart. | Requires the whole check/apply/record transition to be serialized. | None; it can hold even if no message arrives. |
| G2 | An exact retry returns the first chosen semantic response. | Safety: two differing responses are a finite violation. | Requires immutable body/response retention; volatile restart and eviction end the claim. | Requires atomic history lookup relative to insertion. | None for response choice; receiving it additionally needs delivery. |
| G3 | A new valid request has a deterministic next state and response. | Safety/determinism contract: divergent outputs for the same state/input violate it. | Requires the stated map and full history as input; a fresh restart is a different state. | Requires one total event order, supplied by sequential handling. | Handler must have finite inputs/resources to return, but no network progress is claimed. |
| G4 | Valid changed-body ID reuse returns `ID_CONFLICT` and preserves state. | Safety. | Requires the original record; after loss/eviction it may appear first-seen. | Requires lookup and possible insertion to share the atomic boundary. | None. |
| G5 | Equal sequence numbers from different client IDs do not alias history. | Safety. | Requires stable, nonforged client IDs and pair-keyed retained records; not durable across restart. | Same serialization boundary as G1--G4. | None. |
| G6 | A call can eventually obtain a confirmed response. | Conditional liveness. | Server must not crash before/repeatedly during handling; relevant record remains if this is a retry. | State owner must eventually process the delivered event. | At least one attempt is delivered, the finite handler runs, its reply is delivered, and the client remains willing to wait/retry. The given network does not promise these, so unconditional liveness is explicitly absent. |
| N1 | A local timeout determines no unique remote outcome. The API promises only `UNRESOLVED_TIMEOUT`. | Safety-facing non-guarantee; it prevents an unsupported success/failure report and makes no liveness promise. | True with or without retention/crash because the observation is local. | Independent of handler ordering. | None; later resolution needs G6's assumptions. |

Environmental assumptions, rather than derived guarantees, are: **A1** one
noncrashing volatile server in the base model; **A2** atomic sequential delivery
handling; **A3** loss/duplication/finite delay/reordering but no corruption or
forgery; and **A4** conforming stable client identity, positive increasing
sequence numbers, one outstanding operation, and exact-copy retries. If A1 or
A2 is removed, G1--G5 need a new persistence or synchronization argument. If A3
or A4 is removed, integrity, authentication, and session semantics are needed.

### 1.5 Ownership

The **client library owns retry policy**: deadline selection, whether and when
to resend, keeping the same ID/body, and reporting unresolved timeout. The
**server owns duplicate classification** using retained history and atomically
chooses `first_seen`, `exact_retry`, or `id_conflict`. The network owns delivery
and may lose the chosen response; a server response choice is not evidence that
the client observed it.

## 2. State-transition design

### 2.1 Minimal logical state

```go
type RequestID struct { ClientID string; Seq uint64 }
type Kind uint8 // Put, Append, Get
type Body struct {
    Kind Kind
    Key string
    ArgTag uint8 // Value, Suffix, or NoArgument
    Arg string   // empty when ArgTag is NoArgument
}
type Response = OK | VALUE(string) | NOT_FOUND |
                ID_CONFLICT | INVALID_REQUEST(Code)
type Record struct { Body Body; Response Response }
type State struct {
    KV      map[string]string
    History map[RequestID]Record
}
```

Presence in `KV` is distinct from an absent key, so `Get` can distinguish an
empty stored value from `NOT_FOUND`. Mutation application counts used in traces
are harness evidence, not required logical server state. Reply delivery state is
also outside the server state.

### 2.2 Transition function and decision table

The transition has input `(State, raw request)` and output
`(next State, classification, semantic Response)`. Validation is deterministic.
The history check, map read/write, response selection, and history insertion are
one indivisible server transition; sending the reply happens afterward.

```text
handle(raw):
  validated = validate_and_canonicalize(raw)
  if invalid(validated):
      return state, malformed, INVALID_REQUEST(validated.reason)

  rid, body = validated.rid, validated.body
  atomically over both KV and History:
      if rid in History:
          rec = History[rid]
          if rec.Body == body:
              return state, exact_retry, rec.Response
          return state, id_conflict, ID_CONFLICT

      if body.Kind == Put:
          KV[body.Key] = body.Arg
          response = OK
      else if body.Kind == Append:
          old = KV[body.Key] if present, otherwise ""
          KV[body.Key] = old + body.Arg  // creates presence even if both empty
          response = OK
      else: // Get
          response = VALUE(KV[body.Key]) if present, otherwise NOT_FOUND

      History[rid] = Record{Body: body, Response: response}
      return state, first_seen, response
```

| Condition after validation | History action | Map action | Classification / response |
|---|---|---|---|
| `rid` absent, `Put` or `Append` | Insert canonical body and `OK` in same transition as write | Apply operation once | `first_seen / OK` |
| `rid` absent, `Get`, key present | Insert body and `VALUE(v)` | Unchanged | `first_seen / VALUE(v)` |
| `rid` absent, `Get`, key missing | Insert body and `NOT_FOUND` | Unchanged | `first_seen / NOT_FOUND` |
| `rid` present, bodies equal | Read record; no write | Unchanged | `exact_retry / retained response` |
| `rid` present, bodies differ | Read record; no write | Unchanged | `id_conflict / ID_CONFLICT` |
| Validation fails | No read or write | Unchanged | `malformed / INVALID_REQUEST(code)` |

### 2.3 Retention, growth, and future synchronization

The chosen honest policy is **retain every first-seen valid request record until
this process incarnation ends; never evict in the base design**. Thus arbitrary
delayed duplicates remain classifiable during that incarnation. The weaker
behavior begins at the first record eviction or at volatile process loss: from
that exact point, a later attempt for that ID can be classified first-seen.

After `N` first-seen valid logical requests from `C` clients, history has exactly
`N` records. With bounded field sizes this is `O(N)` entries and bytes (or
`O(C+N)` if client strings are interned); no separate per-client table is
needed. More honestly for unbounded strings, byte use is
`Theta(sum of retained ID, body, and response lengths)`, so `N` alone cannot
bound memory. The application map has separate growth based on distinct keys.

A future Go implementation would use one state-owner goroutine for both maps.
Handlers would submit validated requests and receive a semantic decision; only
reply I/O occurs outside the owner. This chooses a synchronization boundary but
does not validate races, cancellation, overload, shutdown, or concurrent
execution.

## 3. Executed deterministic traces

These are manual executions of the transition above, not program output. `A1`
means `(A,1)`. `P`, `Ap`, and `G` abbreviate canonical `Put`, `Append`, and
`Get` bodies. `H[A1]=(Ap("x","r"),OK)` shows the complete relevant record;
`absent -> write` includes the required failed lookup. Mutation count is the
cumulative number of map-changing branches entered for the row's `rid` in that
trace. `∅` means an empty map or history.

### T1 — lost reply and exact retry

| Row / delivered request and classification | Map before | Map after | Relevant history read/write | Response choice / network result | Mutation count | Invariants exercised |
|---|---|---|---|---|---:|---|
| T1.1 `Ap(A1,"x","r")`, `first_seen` | `∅` | `{x:"r"}` | `H[A1]` absent -> write `(Ap("x","r"),OK)` | `OK`, lost | A1=1 | I1, I2, I7 |
| T1.2 exact A1, `exact_retry` | `{x:"r"}` | `{x:"r"}` (unchanged) | Read `H[A1]=(Ap("x","r"),OK)`; no write | cached `OK`, delivered | A1=1 | I1, I3, I6 |

The timeout after T1.1 was compatible with an applied mutation. T1.2 resolves
the call without appending a second `r`.

### T2 — delayed old attempt

| Row / delivered request and classification | Map before | Map after | Relevant history read/write | Response choice / network result | Mutation count | Invariants exercised |
|---|---|---|---|---|---:|---|
| T2.1 `P(A1,"x","red")`, `first_seen` | `∅` | `{x:"red"}` | `H[A1]` absent -> write `(P("x","red"),OK)` | `OK`, delivered | A1=1 | I1, I2, I7 |
| T2.2 `Ap(A2,"x","+blue")`, `first_seen` | `{x:"red"}` | `{x:"red+blue"}` | `H[A2]` absent -> write `(Ap("x","+blue"),OK)` | `OK`, delivered | A2=1 | I1, I2, I7 |
| T2.3 delayed duplicate A1, `exact_retry` | `{x:"red+blue"}` | `{x:"red+blue"}` (unchanged) | Read `H[A1]=(P("x","red"),OK)`; no write; A2 record unchanged | cached `OK`, delivered | A1=1 | I1, I2, I3, I6 |
| T2.4 `G(A3,"x")`, `first_seen` | `{x:"red+blue"}` | `{x:"red+blue"}` (unchanged) | `H[A3]` absent -> write `(G("x"),VALUE("red+blue"))` | `VALUE("red+blue")`, delivered | A3=0 | I2, I3, I6 |

Retaining A1 prevents the old delivery from rolling the newer A2 state back.

### T3 — repeated read after intervening state change

| Row / delivered request and classification | Map before | Map after | Relevant history read/write | Response choice / network result | Mutation count | Invariants exercised |
|---|---|---|---|---|---:|---|
| T3.1 `P(A1,"x","red")`, `first_seen` | `∅` | `{x:"red"}` | `H[A1]` absent -> write `(P("x","red"),OK)` | `OK`, delivered | A1=1 | I1, I2, I7 |
| T3.2 `G(B1,"x")`, `first_seen` | `{x:"red"}` | `{x:"red"}` (unchanged) | `H[B1]` absent -> write `(G("x"),VALUE("red"))` | `VALUE("red")`, delivered | B1=0 | I2, I3, I4, I6 |
| T3.3 `P(A2,"x","green")`, `first_seen` | `{x:"red"}` | `{x:"green"}` | `H[A2]` absent -> write `(P("x","green"),OK)` | `OK`, delivered | A2=1 | I1, I2, I7 |
| T3.4 duplicate B1, `exact_retry` | `{x:"green"}` | `{x:"green"}` (unchanged) | Read `H[B1]=(G("x"),VALUE("red"))`; no write | cached `VALUE("red")`, delivered | B1=0 | I3, I4, I6 |

T3.4 is the old logical observation, not a fresh read. A caller wanting the
current value must issue a new sequence number.

### T4 — conflicting identity reuse

| Row / delivered request and classification | Map before | Map after | Relevant history read/write | Response choice / network result | Mutation count | Invariants exercised |
|---|---|---|---|---|---:|---|
| T4.1 `P(A7,"k","v1")`, `first_seen` | `∅` | `{k:"v1"}` | `H[A7]` absent -> write `(P("k","v1"),OK)` | `OK`, delivered | A7=1 | I1, I2, I7 |
| T4.2 `P(A7,"k","v2")`, `id_conflict` | `{k:"v1"}` | `{k:"v1"}` (unchanged) | Read `H[A7]=(P("k","v1"),OK)`; no write | `ID_CONFLICT`, delivered | retained A7=1; conflicting body=0 accepted | I2, I6 |
| T4.3 `G(B1,"k")`, `first_seen` | `{k:"v1"}` | `{k:"v1"}` (unchanged) | `H[B1]` absent -> write `(G("k"),VALUE("v1"))`; A7 unchanged | `VALUE("v1")`, delivered | B1=0 | I2, I4, I6 |

The conflict neither replaces A7's record nor exposes `v1` in its error.

### B1 — deliberate volatile-restart boundary probe

B1 is outside the base model. The external application counter below is test
instrumentation that survives long enough to compare incarnations; it is not
claimed server state.

| Row / event and classification | Map before | Map after | Relevant history read/write | Response choice / network result | Mutation count across incarnations | Boundary result |
|---|---|---|---|---|---:|---|
| B1.1 deliver `Ap(A1,"x","r")`, `first_seen` in incarnation 1 | `∅` | `{x:"r"}` | `H[A1]` absent -> write `(Ap("x","r"),OK)` | `OK`, lost | A1=1 | I1/I7 hold inside incarnation 1 |
| B1.2 crash after transition, outside base model | `{x:"r"}` | volatile state lost | `H[A1]` existed, then is lost with all history | no response event | A1=1 | G1--G5 no longer have their retained-state premise |
| B1.3 restart under stated policy | no surviving state | `∅` | new `H=∅`; no entry read/written | no response event | A1=1 | New incarnation has no evidence of A1 |
| B1.4 deliver exact A1 bytes, `first_seen` in incarnation 2 | `∅` | `{x:"r"}` | `H[A1]` absent -> write `(Ap("x","r"),OK)` | `OK`, delivered | A1=2 | Cross-restart at-most-once is not established |

The final value happens to equal the pre-crash value because both map and
history were lost; the transition was nevertheless applied twice. A concrete
extension is a durable transactional store whose single crash-atomic commit
contains both the key/value update and the immutable `(rid, body, response)`
record. Recovery must expose either neither item or both before accepting
retries. This names required atomicity but does not validate a storage engine,
disk fault model, concurrent recovery, or replication, and it does not design
consensus.

## 4. Deterministic verification plan

These nine tests are bounded specifications for a direct transition harness;
they have **not** been implemented or run. `DROP_REQ(r)` omits `r` from the
server's delivered-event sequence, and `DELIVER(r, lose_reply)` invokes the pure
transition but withholds the already chosen response from the client. Thus loss
is controlled data, not timing.

| Test / invariant and risk | Exact initial state and event sequence | Expected responses and final map/history | Failure signature | Why no time, network, scheduler, or randomness is needed |
|---|---|---|---|---|
| **V1 Request lost before delivery** — N1; do not invent remote execution | `M=∅, H=∅`; `DROP_REQ(Ap(A1,"x","r"))`; client records timeout; then `DELIVER` the exact A1 and deliver reply | Client observations `[UNRESOLVED_TIMEOUT(A1), OK]`; server response sequence `[OK]`; final `M={x:"r"}`, `H[A1]=(Ap("x","r"),OK)` | Any state/history after the drop, or final `x="rr"` | A drop is omission from an explicit event list; the transition is called once, with no clock or socket |
| **V2 Reply loss plus duplicate non-idempotent mutation** — I1/I3/I7 | `M=∅, H=∅`; `DELIVER(Ap(A1,"x","r"), lose_reply)`; then deliver exact A1 and its reply | Chosen responses `[OK, OK]`, client observations `[UNRESOLVED_TIMEOUT(A1), OK]`; final `M={x:"r"}`, one A1 application, one retained A1 record | `x="rr"`, application count 2, missing record, or second response not `OK` | Reply disposition is a Boolean harness field after each synchronous transition |
| **V3 Delayed old attempt** — I1/I2; stale delivery must not roll back newer state | `M=∅, H=∅`; deliver `P(A1,"x","red")`, `Ap(A2,"x","+blue")`, then duplicate A1 | Responses `[OK, OK, OK]`; final `M={x:"red+blue"}`; `H[A1]=(P("x","red"),OK)`, `H[A2]=(Ap("x","+blue"),OK)`; each applies once | Final `x="red"`, changed A1 record, or A1 count 2 | The adverse order is literal array order, not scheduler order or delayed wall time |
| **V4 Duplicate read after mutation** — I3/I6; repeated read must not become fresh | `M=∅, H=∅`; deliver `P(A1,"x","red")`, `G(B1,"x")`, `P(A2,"x","green")`, duplicate B1 | `[OK, VALUE("red"), OK, VALUE("red")]`; final `M={x:"green"}`; B1 record is `(G("x"),VALUE("red"))` alongside A1/A2 | Last response `VALUE("green")`, map change on either read, or changed B1 record | Four direct calls encode all interleaving; there is no concurrent scheduler |
| **V5 Equal sequence numbers across clients** — I4; false identity alias | `M=∅, H=∅`; deliver `Ap(A1,"x","a")`, then `Ap(B1,"x","b")` | `[OK, OK]`; final `M={x:"ab"}`; distinct A1 and B1 records; application count 1 each | `ID_CONFLICT`, one missing record, or final `x="a"` | Fixed IDs and order directly exercise pair-key lookup, without randomness |
| **V6 All valid conflict dimensions** — I2/I6; changed body must not execute | `M=∅, H=∅`; deliver `P(A7,"k","v1")`; then under A7 deliver `Ap("k","!")` (operation change), `P("other","v1")` (key change), and `P("k","v2")` (argument change) | `[OK, ID_CONFLICT, ID_CONFLICT, ID_CONFLICT]`; final `M={k:"v1"}` with no `other`; sole A7 record remains `(P("k","v1"),OK)`; A7 applies once | Any `!`, `other`, or `v2` map effect; record replacement; a non-conflict response | Body variants are fixed table inputs and equality is exact |
| **V7 Fresh-instance replay determinism** — I5; hidden or time-dependent state | Create two separate fresh `M=∅,H=∅` instances. On each deliver the identical list: `P(A1,"x","red")`, `G(B1,"x")`, `Ap(A2,"x","+b")`, duplicate B1, conflicting `P(A1,"x","blue")` | Both produce `[OK, VALUE("red"), OK, VALUE("red"), ID_CONFLICT]`, final `M={x:"red+b"}`, and identical records A1=`(P red,OK)`, B1=`(G,VALUE("red"))`, A2=`(Ap +b,OK)` | Any pairwise difference in classifications, responses, final map, or history | Instantiate plain data twice and compare structural values; no seed, clock, or external service |
| **V8 Volatile crash boundary** — boundary of I1/G1 | Execute B1: fresh incarnation 1 delivers A1 append and loses reply; discard both maps; fresh incarnation 2 delivers exact bytes | Client sees `[UNRESOLVED_TIMEOUT(A1), OK]`; final incarnation-2 `M={x:"r"}`, one A1 record there; external count is 2 applications across incarnations | A test or documentation claim of cross-restart count 1 under volatile state, or accidental state survival | Restart is construction of a new empty `State`, not a real process crash or sleep; this test demonstrates a non-guarantee |
| **V9 Malformed input and cached missing read** — I3/I6; rejection side effects and `NOT_FOUND` stability | `M=∅, H=∅`; deliver invalid `P("",1,"z","bad")`; deliver `G(A1,"z")`; deliver `P(B1,"z","v")`; duplicate A1 | `[INVALID_REQUEST(EMPTY_CLIENT), NOT_FOUND, OK, NOT_FOUND]`; final `M={z:"v"}`; no invalid-request record; A1=`(G("z"),NOT_FOUND)`, B1=`(P("z","v"),OK)` | State after invalid request, a record for empty client, or final duplicate read `VALUE("v")` | The validator and transition receive four literal values synchronously |

### Bounded property-style check

For every finite delivered-request sequence `E` in the base model and every
`rid`, while no history is discarded: (a) the mutation-application count for
`rid` is at most one; (b) all deliveries whose canonical body equals the first
retained body return the same semantic response; and (c) all different-body
deliveries after retention leave map and history unchanged and return
`ID_CONFLICT`.

A small exhaustive generator could use clients `{A,B}`, sequences `{1,2}`, key
`{x}`, operations `{Put,Append,Get}`, arguments `{"","p"}`, and response-loss
flags. It would enumerate lists through a stated length such as 5, execute the
transition from fresh state, maintain an independent per-ID application count,
and check (a)--(c) after every prefix. Request loss is represented by omitting an
attempt; duplicates and reordering arise from repeated/permuted list elements.
This would be a useful bounded counterexample search, not a proof for arbitrary
lengths, strings, crashes, or concurrent implementations. It remains
unimplemented in this submission.

## 5. Operability and production gaps

### 5.1 Privacy-conscious decision log

One structured event is emitted per server decision, after the transition. This
is an operational proposal, not implemented instrumentation.

```text
DecisionEventV1 {
  observed_at                 // diagnostic timestamp, never ordering evidence
  protocol_version
  server_incarnation_token
  attempt_event_id            // unique only for log correlation
  rid_token                   // HMAC(log-key, canonical client_id || seq)
  body_token                  // HMAC(log-key, canonical request body)
  operation                   // PUT | APPEND | GET | UNKNOWN
  classification              // first_seen | exact_retry | id_conflict | malformed
  history_action              // inserted | read | none
  response_class              // OK | VALUE | NOT_FOUND | ID_CONFLICT | INVALID
  invalid_reason              // bounded code or NONE
  map_mutated                 // boolean
  history_entries_after
  processing_us               // observation only
}
```

The HMAC key is access-controlled and not written to logs. Tokens let an
operator correlate attempts and detect multiple bodies for one ID without
logging raw client IDs, sequence numbers, keys, values, suffixes, or returned
values. Operation and response *classes* are logged, never payloads. Token
access and retention still need a production privacy review; even a keyed token
is not a claim that low-entropy data is harmless.

### 5.2 Metrics

No metric uses client, request, body, key, or incarnation as a label.

| Metric | Type / unit | Bounded labels | Question answered |
|---|---|---|---|
| `courierkv_decisions_total` | Counter, requests | `operation={put,append,get,unknown}`, `classification={first_seen,exact_retry,id_conflict,malformed}`, `response_class={ok,value,not_found,id_conflict,invalid}` | Is traffic dominated by useful first deliveries, exact retries, client protocol conflicts, or malformed input? |
| `courierkv_mutation_applications_total` | Counter, mutation applications | `operation={put,append}` | Are map applications tracking first-seen mutation decisions, or does instrumentation expose an impossible extra application? |
| `courierkv_history_entries` | Gauge, retained records | `store={volatile}` | How close is immutable request history to its entry budget, and did an unexpected reset occur? |
| `courierkv_history_bytes_estimate` | Gauge, bytes | `store={volatile}` | Is variable-sized cached identity/body/response data approaching the memory budget? |

An alert on the mutation counter cannot itself prove I1: correlation and
instrumentation can be wrong. It is an incident signal to compare against
decision logs and deterministic tests.

### 5.3 Incident query

Over a chosen operational window, aggregate tokens without returning them:

```sql
WITH per_rid AS (
  SELECT rid_token,
         COUNT(*) AS attempts,
         SUM(classification = 'exact_retry') AS exact_retries,
         SUM(classification = 'id_conflict') AS conflicts,
         COUNT(DISTINCT body_token) AS body_count
  FROM decision_events
  WHERE observed_at >= :window_start
  GROUP BY rid_token
)
SELECT
  SUM(attempts) AS attempts,
  SUM(exact_retries) AS exact_retries,
  SUM(conflicts) AS conflicts,
  SUM(body_count = 1 AND exact_retries > 0) AS retrying_ids,
  SUM(body_count > 1) AS multi_body_ids
FROM per_rid;
```

A retry storm has many `exact_retries`/`retrying_ids` but mostly one body per ID
and few conflicts. Conflicting reuse has `id_conflict` decisions and
`multi_body_ids`. The window diagnoses running behavior; it has no role in
duplicate correctness or retention expiry.

### 5.4 Capacity estimate and alert

The given model has unbounded string sizes, so it admits **no finite worst-case
history-byte estimate**. For a planning scenario only, suppose measured average
retained ID/body/response data is 160 bytes and hash-table/object overhead is 96
bytes per record. Then 10,000,000 records require about 2.56 GB raw; applying a
1.5 allocator/headroom factor gives about 3.84 GB, excluding the application
map, logs, and process runtime. These assumptions must be replaced by measured
sizes and explicit request limits.

For an example 4 GiB history budget, alert when
`courierkv_history_bytes_estimate > 0.70 * 4 GiB` continuously for 10 minutes.
The window avoids a noisy operational page; it is not a correctness clock.
Because the base policy forbids eviction, crossing the budget is a capacity
incident, not permission to discard records silently.

### 5.5 Ranked production gaps

1. **Crash-atomic durability and recovery.** The current map and deduplication
   evidence vanish together. A concrete next artifact is a durable transactional
   prototype plus crash injection before, during, and after commit, verifying
   recovery exposes both mutation and response record or neither.
2. **Replica agreement, leader/fencing rules, and failover semantics.** A single
   ordered state machine does not decide one order among servers. This needs a
   specified replication protocol, model/linearizability checking, and
   partition/crash tests; none exists here.
3. **Bounded session/history lifecycle under concurrency and overload.** The
   no-eviction policy is not sustainable, client identity is unauthenticated,
   and the goroutine note is unvalidated. A future session/acknowledgment rule,
   quotas, race tests, fuzzing, load tests, and privacy/security review would be
   required before safe collection or production operation.

### 5.6 What each evidence source can say

The completed T1--T4 and debugging cycles are deterministic desk evidence about
specific model transitions. V1--V9 and the generator are proposed verification
artifacts and therefore provide no executed results yet. If implemented, they
could expose model/implementation disagreement within their bounds. Logs and
metrics would only observe a running system's decisions, latency, retries,
conflicts, resets, and capacity. They cannot prove invariants, exhaustive
behavior, durable crash safety, or replica agreement.

## 6. Comprehension responses

### C1 — What did the timeout reveal?

The timeout reveals only that the client observed no matching reply before its
local deadline. In one compatible history, the request is lost before delivery,
so the server's map and history remain unchanged; V1 encodes this as an omitted
delivery. In another, the server receives the `Append`, atomically changes the
map, retains `OK`, and the reply is lost, as in T1.1. A delayed request or reply
is also compatible. At the deadline the client may safely report
`UNRESOLVED_TIMEOUT(rid)` and retain the option to resend the exact same ID and
body. Saying “the append failed,” “the server did nothing,” or “the append
succeeded” would select one indistinguishable history and overclaim. N1 decides
the immediate API behavior; a later confirmed response needs G6's delivery and
processing assumptions.

### C2 — What makes an operation the same operation?

`seq` is monotonic only within a client session, so A1 and B1 are both legal and
different; debugging cycle 3 shows that a sequence-only table falsely rejects
B1. My system-wide logical identity is `(client_id,seq)`. Within that pair,
canonical body equality identifies an exact retry and causes the stored response
to be replayed. The same pair with a changed valid operation, key, or argument
is conflicting reuse and receives `ID_CONFLICT` without state change, as T4.2
shows. A different `client_id` with the same number indexes another history
record, as required by I4 and proposed test V5. Each client's request-history
namespace must remain isolated; the key/value map is intentionally shared and
can reflect accepted operations from either client.

### C3 — Safety, liveness, and assumptions

G1, “one accepted mutation is applied at most once,” is safety: a trace prefix
containing its second application permanently demonstrates the violation.
Within the base model it depends on retained history, a noncrashing incarnation,
and serialized check/apply/record atomicity, but it needs no message progress.
G6, eventual receipt of a confirmed response, is conditional liveness because
it says a desired event eventually occurs. Its minimum progress premises are
that at least one attempt is delivered, the noncrashed server/state owner gets
scheduled and terminates on the finite input, the selected reply is delivered,
and the client remains willing to wait or retry. The supplied network may lose
every attempt or reply, so those premises are environmental assumptions rather
than consequences of the transition function; no unconditional liveness claim
is made.

### C4 — How much history is enough?

Remembering only the newest request per client is insufficient under the allowed
delay. In T2, retaining A2 would evict A1 after `Append` creates
`red+blue`. The delayed A1 `Put` would then look first-seen, execute a second
time, and replace the value with `red`; debugging cycle 1 preserves this exact
counterexample. Its response happens still to be `OK`, but I1 is violated, and
an evicted old `Get` could also violate I3 by observing a newer value. My
alternative retains every first-seen valid body and response for the entire
incarnation, costing `O(N)` entries and variable bytes. Safe bounded collection
would require a new protocol premise—such as authenticated session epochs plus
an acknowledgment/watermark proving old IDs cannot return—not a wall-clock
cache timeout.

### C5 — Is a repeated read a new read?

The second delivery of `Get(B,1,"x")` in T3 has the same full ID and canonical
body, so it is another attempt for B1, not another logical read. T3.2 fixed
B1's response as `VALUE("red")`. After A2 changes the map to `green`, T3.4 must
return the cached `VALUE("red")` while leaving the current map unchanged. If the
client wants a fresh observation, it must issue `Get(B,2,"x")` (or another new
positive sequence) so the server evaluates a first-seen operation. Treating the
duplicate as fresh would produce two client-visible results for one operation.
Required behavior 2 is captured by I3, stable semantic response, and I6 ensures
neither read delivery mutates the map.

### C6 — What changes at restart?

In B1, volatile restart erases both `x="r"` and the A1 record containing its
body and `OK`. The retry therefore looks first-seen in incarnation 2 and enters
the append branch again. Although the final restarted map is again `x="r"`, the
cross-incarnation application count is 2, so G1 is no longer established; the
same missing record also removes the basis for G2 and conflict detection. One
concrete remedy is a durable transactional store that commits the map mutation
and immutable `(rid, body, response)` record as one crash-atomic unit and restores
both before requests resume. It must never recover just one side. This proposal
does not prove the store's crash behavior, concurrent recovery, disk integrity,
client-session recovery, replication, or consensus; V8 remains only a volatile
boundary test.

### C7 — Why is this not consensus?

The transition function deterministically consumes an order already supplied to
one server; it does not cause several servers to choose the same order when they
receive messages differently or become partitioned. One absent question is who
may act as leader and how stale leaders are fenced across failures. Future
evidence would need term/lease rules plus partition and failover traces showing
that conflicting leaders cannot both commit. A second absent question is when a
replicated operation is committed and survives replica crashes or membership
change. That would require a specified replication/quorum protocol and evidence
such as model-checked safety properties plus recovery/linearizability tests under
message loss and reordering. The single-server tables, including I5 and V7,
answer neither question and therefore provide no consensus evidence.

## 7. Final self-audit

### Claim-to-evidence table

| Claim | Concrete evidence | Honest limit |
|---|---|---|
| Retry of an accepted mutation does not apply it again in the base state. | T1.1--T1.2; T2.3; debugging cycle 1 rerun | Manually desk-checked examples, not proof or executable validation |
| Exact retries replay their selected semantic result. | T1.2 and T3.4; debugging cycle 2 rerun | Only named traces executed; V2/V4 remain plans |
| Client namespaces do not alias on equal sequence numbers. | I4 and debugging cycle 3 rerun | V5 not implemented; stable/authentic IDs assumed |
| Changed valid bodies under one retained ID preserve state. | T4.1--T4.3 and transition conflict row | Only argument-change trace executed; V6's op/key variants unexecuted |
| Timeout cannot establish remote execution state. | Two compatible histories in C1, T1, and planned V1 | No real network experiment; it is a model-level conclusion |
| Ordered-event handling is deterministic. | Complete transition table and matching manual traces | Fresh replay V7 and exhaustive generator were not run; concurrency absent |
| Volatile restart ends the retry-safety guarantee. | B1 and debugging cycle 4 | Boundary was desk-checked, not crash-injected against storage |

### Unresolved risks and unperformed checks

- No source code, unit tests, property generator, race detector, fuzzing, crash
  injection, storage validation, networking, benchmark, or load test was run.
- String encoding/normalization, request and response size limits, authentication,
  sequence recovery, overload, cancellation, and safe shutdown remain open.
- History has no safe bounded-retention protocol and may exhaust memory.
- The HMAC logging scheme, capacity figures, metrics, alert, and incident query
  are designs only; privacy and operational behavior are unvalidated.
- Durable transactions, multiple replicas, leader election, log agreement,
  membership, failover, and consensus are outside this unit and unproved.

Actual time spent on this attempt was approximately 35 minutes, measured
coarsely; the 8-hour hard stop was not reached. No external course material,
public solution, course link, or implementation reference was used. I do not
claim completion of MIT6.824 or of any official assignment.

**locally authored kickoff; no official course credit**
