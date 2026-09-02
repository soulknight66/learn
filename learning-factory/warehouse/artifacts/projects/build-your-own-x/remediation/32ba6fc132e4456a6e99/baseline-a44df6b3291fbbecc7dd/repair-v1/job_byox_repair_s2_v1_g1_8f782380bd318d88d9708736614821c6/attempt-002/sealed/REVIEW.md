# Sealed implementation review

## Review outcome

Repair-generation review found the reference appropriate for an educational
single-process model. The public and sealed suites exercise its main safety
boundaries. This is not a production-readiness approval, and the manifest
therefore remains `productionized: false` with `GENERATED` and `PARTIAL` only.

## Positive properties checked

- Arrays cross API boundaries by copy.
- The complemented length is checked before allocation or torn-tail
  classification; allocation is bounded and CRC is checked before metadata is
  accepted.
- Offset continuity is checked across records and segment filenames.
- Locale-neutral segment creation matches ASCII-only discovery.
- Only a structurally identified torn suffix of the last segment is repaired
  automatically; corrupt length pairs and complete corrupt frames are
  preserved.
- Terms, replica positions, and the watermark cannot regress through public
  operations.
- Fixed-majority commitment is independent from diagnostic ISR membership.
- Test runners use argv arrays, captured output, explicit scratch-root
  selection, timeouts, new process groups, and group termination on timeout.

## Known gaps and risks

- A complemented length and CRC32 detect accidental damage but are not
  cryptographic integrity; coordinated field rewrites are outside the fault
  model.
- Election term and vote are not durable; this is not a complete consensus
  implementation.
- There is no follower log reconciliation, exclusive directory lock, directory
  fsync after segment creation, retention, sparse index, or concurrent writer
  support.
- A filesystem may complete bytes even when `force` reports an error. The
  instance is poisoned, but callers still need restart/recovery and request
  deduplication semantics.
- All recovered record payloads remain in heap memory.
- No network, authorization, quotas, overload behavior, or operational tooling
  is implemented or tested.

These gaps are intentional scope boundaries, not deferred claims of readiness.
