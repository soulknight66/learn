# Debugging Log

This log records externally checkable hypotheses, experiments, results, and design lessons. It does not claim test outcomes that were not observed.

## 2026-08-31 — Toolchain availability

- **Hypothesis:** the local Go toolchain can format and execute the kickoff package.
- **Experiment:** ran `go version` from the workspace root, then from `submission/` attempted `gofmt -w authzstore`, `go vet ./...`, `go test ./...`, and `go test -race ./...`.
- **Observed result:** every tool command failed with exit status `127`; the shell reported `go: command not found` or `gofmt: command not found`.
- **Consequence:** no formatting, compilation, vet, unit-test, or race-detector success is claimed. Literal evidence is preserved in `submission/EVIDENCE.md`.
- **Lesson:** environmental failure is part of the evidence. It must remain distinguishable from a code or test pass.

## Representation-aliasing hypothesis

- **Hypothesis:** storing or returning a caller slice directly would let a later byte mutation bypass the owner-only replacement policy.
- **Experiment authored:** `TestStoreOwnsInputAndOutputSlices` changes the original create buffer, the replacement buffer, and returned read buffers, then re-reads stored state. It retains a prior read across replacement as a snapshot check.
- **Expected discriminator:** a missing copy causes a payload mismatch at the first relevant re-read; correct ownership keeps stored `"alpha"`/`"bravo"` independent.
- **Execution status:** not run because the Go toolchain is unavailable.
- **Lesson:** ownership of mutable representations needs tests at both API directions, not just a comment.

## Collision-handling hypothesis

- **Hypothesis:** checking a generated ID without making check-and-insert atomic can overwrite or race with an existing document.
- **Experiment authored:** a controlled source emits A for the first document and A, B for the second. `TestControlledIdentifierCollisionDoesNotOverwrite` expects the retry to return B and independently verifies both owners and payloads. A second test returns A forever and expects bounded, non-mutating failure.
- **Expected discriminator:** overwrite-on-collision changes A's owner or payload; unbounded retry hangs; correct behavior preserves A and either commits B or returns `ErrIdentifierGeneration`.
- **Execution status:** not run.
- **Lesson:** unpredictability, uniqueness checking, collision retry, and failure bounds are separate requirements.

## Revocation/concurrency hypothesis

- **Hypothesis:** if authorization lookup and payload copying do not share a synchronization interval, a check/use gap can let a post-revocation read succeed or expose a torn payload.
- **Experiment authored:** one `RWMutex` covers policy lookup through copy and every mutation. `TestReadBeginningAfterRevokeReturnsIsDenied` uses channel ordering; concurrent grant/revoke/read and replace/read tests use start barriers and wait groups, never `time.Sleep`.
- **Expected discriminator:** overlapping reads may legitimately succeed or fail according to linearization order, but a read started after completed revoke must fail and payloads must equal one complete writer value.
- **Execution status:** not run, including under `-race`.
- **Lesson:** concurrency policy should name both real-time guarantees and permitted overlap outcomes.

## Denied-mutation hypothesis

- **Hypothesis:** an authorization failure could still partially change payload, grants, owner authority, or liveness if mutation precedes all checks.
- **Experiment authored:** each denied role case reconstructs a fresh fixture and checks the relevant state afterward. Malformed-input cases re-read both owner and grantee views; a fixed-seed model audits all principals after every random action.
- **Expected discriminator:** any partial mutation changes a later payload, allowed/denied read, owner-only action, or live/deleted observation.
- **Execution status:** not run.
- **Lesson:** “returned an error” is not proof of fail-closed behavior; post-state needs an oracle.

