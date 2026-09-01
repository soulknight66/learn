# Study Task: Build a Fail-Closed Authorization Core

## Scenario

Build a small Go package named `authzstore` that stores document bytes in memory and enforces an owner/read-share policy. Treat it as a policy engine behind a trusted identity adapter, not as a network service or a complete secure file-sharing system.

Your goal is to make the security argument inspectable: define the boundary, state the invariants, implement them, and try to break them with tests.

## System model

- Each document has an opaque identifier, one owner, a byte payload, and a set of principals granted read access.
- A trusted adapter supplies a nonempty caller principal. Authentication itself is out of scope.
- Document identifiers, payloads, and operation parameters are otherwise untrusted inputs.
- Multiple goroutines may call the same store concurrently.
- Callers cannot inspect process memory except through the package API.

Implement these operations with a clear, documented Go API:

- create a document;
- read a document;
- replace its payload;
- grant read access to a principal;
- revoke a principal's read access; and
- delete a document.

## Required policy and invariants

1. The owner may perform every operation on a live document.
2. A principal with a read grant may only read that document.
3. Every other request is denied by default.
4. Granting and revoking are owner-only. Revocation affects every later read that begins after the revoke operation completes.
5. Deletion is owner-only and removes all later access.
6. A denied operation makes no state change. Define deterministic behavior for repeated grant, revoke, and delete attempts.
7. For a syntactically valid identifier, denied, unknown, and deleted documents have the same public error classification. Do not create a document-existence oracle for unauthorized callers.
8. The store owns its bytes: copy mutable byte slices at API boundaries so later caller mutations cannot change stored state or prior read results.
9. Each operation is atomic from a caller's perspective and the implementation is race-free. Do not invoke callbacks or potentially blocking randomness while holding a state lock unless your design justifies it.
10. Production identifiers use `crypto/rand` with at least 128 bits of randomness and are encoded as opaque strings. Handle a generated collision without overwriting an existing document.
11. Malformed inputs return documented errors without panics, partial mutation, payload disclosure, or sensitive logging.

Use only the Go standard library. Keep the component in memory; do not add a server, database, command-line interface, encryption scheme, or third-party package.

## Engineering artifacts

Create the following:

### `submission/THREAT_MODEL.md`

State:

- protected assets and security goals;
- actors and attacker capabilities;
- trust boundaries and trusted inputs;
- explicit assumptions and exclusions; and
- at least four concrete abuse cases, each linked to a mitigation and a way to verify it.

At least one abuse case must concern authorization, one representation aliasing, and one concurrency or state-transition failure.

### `submission/DESIGN.md`

Include:

- an operation-by-role authorization table;
- state invariants before and after every operation;
- public error categories and what information they reveal;
- your lock or synchronization strategy and operation linearization points;
- ownership rules for input and output byte slices; and
- identifier generation, encoding, collision handling, and testability.

Explain the choices made; a code outline alone is insufficient.

### Go implementation and tests

Place `go.mod` under `submission/` and package code and tests under `submission/authzstore/`.

Tests must cover:

- every operation for owner, read-granted, and unrelated roles;
- grant, revoke, replace, and delete state transitions;
- identical public denial classification for unknown and inaccessible identifiers;
- mutation of input and returned byte slices;
- malformed input and failure paths with no partial mutation;
- an injected or otherwise controlled identifier source that produces a collision;
- concurrent access under the race detector without timing sleeps; and
- at least one model-based, randomized, or fuzz test that checks an invariant rather than merely checking for a crash.

Keep tests deterministic when given a fixed seed. Use synchronization primitives or barriers instead of `time.Sleep` to coordinate concurrency tests.

### `submission/COMPREHENSION.md`

Respond to every prompt in [COMPREHENSION.md](COMPREHENSION.md). Connect each response to your own design or a named test.

### `submission/EVIDENCE.md`

Record:

- the Go version used;
- exact commands executed;
- exit status and relevant output for formatting, vetting, normal tests, and race-enabled tests; and
- a short mapping from each required invariant to the test or inspection that supports it.

Run, at minimum, from `submission/`:

```text
gofmt -w authzstore
go vet ./...
go test ./...
go test -race ./...
```

If a command cannot run, record the blocker and do not report it as successful.

## Final self-review

Before submission, verify that the implementation does not claim to provide authentication, network confidentiality, durable storage, or production file sharing. Make sure negative paths are deliberate, documented, and tested.
