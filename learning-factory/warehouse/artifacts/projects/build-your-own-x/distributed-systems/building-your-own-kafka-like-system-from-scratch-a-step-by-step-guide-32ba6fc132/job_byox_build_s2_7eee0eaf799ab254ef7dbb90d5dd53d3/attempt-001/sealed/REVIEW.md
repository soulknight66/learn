# Sealed implementation review

## Review outcome

Generation-time review found the reference appropriate for an educational
single-process model. The public and sealed suites exercise its main safety
boundaries. This is not a production-readiness approval, and the manifest
therefore remains `productionized: false` with `GENERATED` and `PARTIAL` only.

## Positive properties checked

- Arrays cross API boundaries by copy.
- Frame allocation is bounded before allocation and CRC is checked before
  metadata is accepted.
- Offset continuity is checked across records and segment filenames.
- Only a torn suffix of the last segment is repaired automatically.
- Terms, replica positions, and the watermark cannot regress through public
  operations.
- Fixed-majority commitment is independent from diagnostic ISR membership.
- Test runners use argv arrays, captured output, timeouts, and temporary build
  directories.

## Known gaps and risks

- The length prefix lacks independent integrity, leaving the final-frame
  ambiguity described in `DESIGN.md`.
- Election term and vote are not durable; this is not a complete consensus
  implementation.
- There is no follower log reconciliation, exclusive directory lock, directory
  fsync after segment creation, retention, sparse index, or concurrent writer
  support.
- A filesystem may complete bytes even when `force` reports an error. The
  instance is poisoned, but callers still need restart/recovery and request
  deduplication semantics.
- All recovered record payloads remain in heap memory.
- CRC32 detects accidental changes but offers no adversarial integrity.
- No network, authorization, quotas, overload behavior, or operational tooling
  is implemented or tested.

These gaps are intentional scope boundaries, not deferred claims of readiness.
