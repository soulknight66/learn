# Study Task: Retry-Safe CourierKV Design Dossier

## Goal and timebox

Produce a contract and deterministic verification dossier for the fictional
CourierKV service below. The result must be precise enough that one engineer
could implement it in Go and another could derive tests without asking what its
central guarantees mean.

Plan for 6 hours and stop after 8. This is a design-and-evidence exercise, not a
request to build a network service or recover an official course assignment.

## Submission files

Write exactly these learner artifacts:

- `notes.md`: assumptions, alternatives considered, open questions, and a
  claim-to-evidence index;
- `submission.md`: the final contract, state-transition design, completed
  trace tables, deterministic test plan, operability review, boundary analysis,
  and answers to the comprehension prompts; and
- `debugging-log.md`: the reproducible experiment and revision record described
  below.

Keep final conclusions in `submission.md`; the other two files are supporting
evidence. If time expires, identify incomplete sections and the next discriminating
experiment. Do not report unperformed work as evidence.

## The CourierKV model

CourierKV has one server and an initially empty map from string keys to string
values. It accepts three logical operations:

```text
Put(client_id, seq, key, value)
Append(client_id, seq, key, suffix)
Get(client_id, seq, key)
```

For this unit:

- `client_id` is a nonempty stable string.
- `seq` is a positive integer, increasing within one client's session.
- The logical request ID is the pair `(client_id, seq)`.
- A conforming client has at most one logical request outstanding and sends an
  exact copy, including the same request ID and body, when it retries.
- Different clients may use the same sequence number.
- `Put` replaces a value. `Append` appends to the current value and treats a
  missing key as empty. `Get` returns `VALUE(value)` or `NOT_FOUND`.
- A successful mutation returns `OK`. A conflicting reuse of an ID may return
  `ID_CONFLICT`.
- The network may lose a request before delivery, lose a reply, duplicate a
  message, delay it for an arbitrary finite time, or deliver attempts out of
  order. It does not corrupt or forge messages.
- Eventual delivery is not guaranteed. Clocks and delivery timing carry no
  correctness meaning.
- In the base model, the server processes one delivered request atomically at a
  time and does not crash. Its map and request-history metadata are volatile.
- Server crash/restart, durable storage, concurrent handlers, multiple servers,
  replication, and consensus are outside the base model.

## Required service behavior

Your design must make these requirements checkable:

1. One accepted logical `Put` or `Append` changes the map at most once,
   regardless of how many exact attempts are delivered.
2. An exact retry receives a response semantically identical to the response
   chosen for its first delivered attempt. For `Get`, this includes the
   original `VALUE` or `NOT_FOUND` result.
3. A new valid request is handled deterministically from the current map,
   retained request metadata, and request body.
4. Reusing a request ID with a different operation, key, or argument must not
   silently apply a second operation. Define its client-visible result and
   preserved state.
5. The client-facing contract must say what can and cannot be concluded after a
   local timeout.
6. Every guarantee must state its retention, crash, concurrency, and progress
   assumptions. Do not use “exactly once” as an unqualified slogan.

## Part 1: Contract and invariants

In `submission.md`:

1. Define the request and response vocabulary, including malformed input,
   protocol-conflicting ID reuse, and local timeout.
2. State the preconditions and postconditions for each operation.
3. Give at least four named invariants (`I1`, `I2`, and so on). Include map
   mutation, request identity/history, stable responses, and cross-client
   isolation.
4. Label each guarantee or non-guarantee as safety, liveness, or an environmental
   assumption, and explain the classification.
5. State which component owns retry policy and which component owns duplicate
   classification.

In `notes.md`, maintain an assumption ledger with the columns: assumption,
source (given or chosen), consequence if false, and where the boundary is
documented.

## Part 2: State-transition design

Specify:

- the server's minimal logical state, with Go-like types or a language-neutral
  schema;
- a transition function with inputs, outputs, and atomicity boundary;
- pseudocode or a complete decision table for a first-seen request, exact retry,
  conflicting ID reuse, and lookup of a missing key;
- what request fingerprint and response information is retained;
- the asymptotic metadata growth after `C` clients and `N` accepted logical
  requests; and
- one honest retention policy. If it weakens a guarantee, identify the exact
  point at which the weaker behavior begins.

Although base events are sequential, add a short implementation note choosing
either one state-owner goroutine or a synchronization boundary for a future Go
implementation. Do not pretend this note validates concurrent execution.

## Part 3: Execute the traces

For every server-delivery event below, record:

- request classification;
- map before and after;
- history entry read or written;
- response chosen and whether it is delivered or lost;
- mutation count for the logical request; and
- the invariant(s) exercised.

Use the response vocabulary from your contract. Do not skip “unchanged” fields.

### T1 — Lost reply and exact retry

Initial state: empty.

1. Deliver `Append(A, 1, "x", "r")`; lose the server's reply.
2. Deliver an exact retry of `Append(A, 1, "x", "r")`; deliver its reply.

### T2 — A delayed old attempt

Initial state: empty.

1. Deliver `Put(A, 1, "x", "red")`; deliver its reply.
2. Deliver `Append(A, 2, "x", "+blue")`; deliver its reply.
3. Deliver a delayed duplicate of `Put(A, 1, "x", "red")`; deliver its reply.
4. Deliver `Get(A, 3, "x")`; deliver its reply.

### T3 — A repeated read after intervening state change

Initial state: empty.

1. Deliver `Put(A, 1, "x", "red")`; deliver its reply.
2. Deliver `Get(B, 1, "x")`; deliver its reply.
3. Deliver `Put(A, 2, "x", "green")`; deliver its reply.
4. Deliver a duplicate of `Get(B, 1, "x")`; deliver its reply.

### T4 — Conflicting identity reuse

Initial state: empty.

1. Deliver `Put(A, 7, "k", "v1")`; deliver its reply.
2. Deliver `Put(A, 7, "k", "v2")`; deliver its reply.
3. Deliver `Get(B, 1, "k")`; deliver its reply.

### B1 — Deliberate boundary probe

This is not a base-model trace. Do not silently extend the model.

1. Deliver `Append(A, 1, "x", "r")`; lose the reply.
2. Crash the server after the map transition.
3. Restart with only the state your stated persistence policy guarantees.
4. Deliver the exact retry.

Explain which base guarantee is no longer established. Then name one concrete
additional persistence or session mechanism and the atomicity it would require;
do not design consensus.

## Part 4: Deterministic verification plan

Define at least eight bounded tests. Each test must include:

- invariant and risk addressed;
- exact initial state and delivered-event sequence;
- expected response sequence and final map/history;
- a failure signature; and
- why no sleep, wall clock, network, scheduler order, or random seed is needed.

Collectively cover request loss before delivery, reply loss, duplicate
non-idempotent mutation, delayed old attempts, duplicate reads after intervening
mutation, equal sequence numbers from different clients, conflicting ID reuse,
fresh-instance replay determinism, and the crash boundary. One test may cover
more than one case.

Add one property-style statement quantified over finite event sequences and show
how a small exhaustive trace generator could check it without claiming a proof.

## Part 5: Operability and production gaps

Provide:

1. a structured decision-log schema that lets an operator correlate attempts
   without logging values or secrets;
2. four named metrics, each with units, labels of bounded cardinality, and the
   failure or capacity question it answers;
3. one incident query that distinguishes a retry storm from conflicting ID
   reuse;
4. a request-history capacity estimate and one alert condition; and
5. a ranked list of the three most important gaps between this model and a
   production replicated service.

Do not claim that logs prove correctness. State which evidence comes from
deterministic verification and which observations would come only from a running
system.

## Part 6: Debugging record

Run at least three desk-check cycles against your current transition design.
Record each in `debugging-log.md` using:

```text
Cycle:
Hypothesis:
Exact initial state and event stream:
Predicted observation:
Observed result from executing the current table or pseudocode:
Discrepancy or confirmation:
Design/test revision:
Rerun result:
Remaining uncertainty:
```

At least one cycle must expose a counterexample to a candidate design. If your
first design survives the supplied traces, test a deliberately simpler
alternative and show exactly where it fails. Preserve that failed alternative
rather than rewriting history.

## Final self-audit

End `submission.md` with:

- a claim-to-evidence table pointing to trace/test/debugging sections;
- a list of unresolved risks and unperformed checks;
- actual time spent and whether the hard stop was reached;
- a statement that no external course material or solution was used; and
- this exact scope label: **locally authored kickoff; no official course credit**.
