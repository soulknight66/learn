# Behavioral requirements

Terms such as **must** and **must not** are testable. Public tests cover only
representative cases.

## R1 — record ownership and identity

- `LogRecord` has a non-negative offset and timestamp, an optional key, and a
  required value.
- Constructors and accessors must defensively copy arrays. Equality and hash
  code compare byte content, not array identity.
- Values larger than the configured record limit must be rejected before any
  file is changed.

## R2 — framed encoding

- A persisted frame contains a bounded length, format marker and version,
  offset, timestamp, nullable-key metadata, value length, payload, and CRC32.
- Decoding must distinguish clean end-of-file, an incomplete final frame, and
  a complete but invalid/corrupt frame.
- Negative lengths, integer overflow, unknown format/version, inconsistent
  null flags, CRC mismatch, and over-limit frames are corruption, not records.

## R3 — segmented durable log

- `SegmentedLog.open` creates a missing data directory and an initial segment.
  Segment names use a 20-digit base offset followed by `.log`.
- Appends assign gap-free offsets starting at zero. A segment rotates before an
  append that would exceed its byte limit, except that one valid frame may
  occupy an otherwise empty segment.
- Reopening reconstructs the next offset and record order from disk.
- Only an incomplete suffix of the final segment may be truncated during
  recovery. Corruption, offset gaps, an incomplete non-final segment, invalid
  names, or overlapping bases must fail without silently rewriting evidence.
- `read` returns records at or after the requested offset, in order, bounded by
  record count and encoded bytes. It must not expose internal mutable arrays.
- `close` is idempotent; operations after close fail predictably.

## R4 — election safety

- `ElectionState` tracks a monotonically increasing term and at most one vote
  per term. Lower-term requests are rejected.
- A higher-term request first advances the local term and clears the old vote,
  even when the new candidate is rejected.
- A candidate is up to date when its last log term is greater, or when terms
  match and its last offset is at least the local last offset. The same
  candidate may repeat a granted request in one term; a different candidate
  may not receive that vote.

## R5 — replication and commitment

- Replica membership is fixed and contains an odd number of at least three
  unique non-blank IDs, including the leader.
- Leader and follower positions are *end offsets*: position `n` means all
  records below `n` are replicated. Positions never regress and cannot exceed
  the leader end offset.
- Acknowledgements from an old leader term are fenced and must not change
  progress. Unknown replicas and future terms fail explicitly.
- The high watermark is the greatest end offset held by a strict majority. It
  is monotonic and never exceeds the leader end offset.
- In-sync status is diagnostic and uses configured record-lag and silence
  limits. Removing a lagging replica from that status must not redefine the
  fixed majority required for commitment.

## R6 — partition behavior

- An append with the active leader term writes exactly one record, then updates
  leader progress. An append with any other term is rejected before mutation.
- `LEADER` reads may observe every local record. `COMMITTED` reads may observe
  only offsets strictly below the high watermark.
- Follower acknowledgements flow through the same fencing and bounds checks as
  `ReplicationTracker`.
- Caller errors must not partially mutate offsets, replica progress, or files.

## R7 — deterministic resource behavior

- The implementation uses only Java standard-library APIs and no wall-clock
  reads internally; callers supply timestamps.
- Disk writes and reads handle short channel operations. Resources are closed
  on normal and exceptional paths.
- Public APIs validate nulls, negative values, zero limits, and illegal state
  with stable Java exception categories.
