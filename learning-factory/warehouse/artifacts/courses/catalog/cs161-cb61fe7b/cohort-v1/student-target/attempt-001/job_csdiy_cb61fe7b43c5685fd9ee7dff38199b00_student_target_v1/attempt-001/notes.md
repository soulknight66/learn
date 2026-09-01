# Kickoff Unit Notes

## Scope checkpoint

This is an attempt at only the course-manager-authored CS161-inspired kickoff: a single-process, in-memory Go authorization core. It is not official UC Berkeley material and is not completion of CS161. Authentication, networking, persistence, encryption, key management, and UI work remain outside the boundary.

## Security model in one page

The component protects payload confidentiality, policy integrity, atomic state transitions, representation ownership, identifier uniqueness, and a coarse no-existence-oracle error API. Its decisive trust assumption is that an adapter has already authenticated the caller. An authorization function cannot repair forged identity input.

The policy is deliberately small:

- any authenticated nonempty principal may create and owns the new document;
- the owner may read, replace, grant, revoke, and delete;
- a grantee may only read;
- all other valid requests return one denial category; and
- malformed inputs fail before state changes.

The state invariant is more useful than a list of happy paths: every live ID has exactly one owner, a store-owned payload, and a reader set; only owner-authorized transitions mutate those fields; denied calls preserve all fields; and an ID is never reused during a store's lifetime.

## Production-engineering lessons practiced

1. **Trust boundaries precede code.** `caller` is an authenticated fact from an adapter, while IDs, target principals, payloads, and schedules are adversarial inputs.
2. **Negative behavior is API behavior.** Unknown, deleted, and inaccessible valid IDs all return `ErrDenied`. Invalid syntax has a separate documented category.
3. **Representation is part of authorization.** A Go slice is a descriptor for shared mutable storage. Copying only the header does not protect bytes, so create/replace inputs and read outputs need deep copies.
4. **Locks support a security argument.** One `RWMutex` spans lookup, authorization, and mutation/copy. This gives each operation a named linearization point and prevents check/use gaps.
5. **Slow dependencies should not sit under the state lock.** Random ID generation happens outside the document lock. A separate generator mutex supports deterministic sources, and the state lock makes collision check plus insertion atomic.
6. **Random identifiers are defense in depth.** They reduce enumeration and correlation but never substitute for owner/grant checks.
7. **Failure evidence must be literal.** A missing toolchain is a blocker, not a passing result. Tests were authored, but their execution is explicitly unverified.

## Test strategy

The test suite is designed around adversarial properties rather than examples alone:

- full operation-by-role cases;
- transition and idempotence traces;
- exact error-category comparisons;
- deliberate mutations of retained slices;
- injected A, A, B identifier collisions and permanent collision failure;
- barrier/channel-coordinated concurrency with no timing sleeps; and
- a fixed-seed model that audits authorization and payload state after every random operation.

The strongest model-test oracle is simple: after any action, each principal either reads the exact modeled payload or receives exact `ErrDenied`; a denied mutation cannot silently alter the next audit.

## Open questions and bounded future work

- A production service would need payload/grant quotas and resource-exhaustion policy.
- A network boundary would require authenticated sessions, transport protection, replay rules, rate limits, and safe request logging.
- Durable revocation/deletion would require crash-consistent storage, rollback and backup policy, and a larger trust model.
- Independent validation should first run formatting, vet, normal tests, and the race detector once a Go toolchain is available.

These are recorded as future work; they were not added to this kickoff.

