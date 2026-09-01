# Kickoff Submission Summary

## Bounded result

I attempted the first, bounded computer-security kickoff only. The result is an in-memory Go package and its security argument; it does not claim authentication, network confidentiality, persistence, encryption, production file sharing, broader-course coverage, or whole-course completion.

## Artifact manifest

- `submission/THREAT_MODEL.md`: assets, actors, trust boundaries, exclusions, and seven abuse-case/mitigation/check mappings.
- `submission/DESIGN.md`: public API, authorization table, invariants, deterministic repeats, errors, slice ownership, synchronization/linearization, and ID collision design.
- `submission/go.mod` and `submission/authzstore/store.go`: standard-library-only implementation.
- `submission/authzstore/store_test.go`: policy matrix, transitions, equalized denials, alias tests, malformed and generator failures, collision tests, synchronized concurrency tests, and fixed-seed model testing.
- `submission/COMPREHENSION.md`: responses to all eight prompts tied to named tests and state traces.
- `submission/EVIDENCE.md`: commands, literal failure outputs, validation labels, and invariant-to-check mapping.
- `notes.md` and `debugging-log.md`: learner notes and reproducible experiment history.

## Design highlights

All document state is protected by one `sync.RWMutex`; authorization and its corresponding observation or state transition occur under that lock. Payload slices are copied on input and output. Production IDs use 16 bytes from `crypto/rand`, collision check/insertion is atomic, retries are bounded, and used IDs remain tombstoned after deletion. Public valid-ID failures collapse to exact `ErrDenied`.

Repeated grant/revoke calls are successful idempotent operations; granting or revoking the owner is also a no-op. A repeated delete returns `ErrDenied` because the ID no longer names a live document.

## Validation status

**Blocked, not passed.** `go` and `gofmt` are unavailable on this workspace's `PATH`. The required formatting, vet, normal-test, and race-test commands were attempted and each exited `127`; exact outputs are in `submission/EVIDENCE.md`. The tests therefore remain authored but unexecuted here, and independent worker-harness validation is still required.

