# Behavioral requirements

Terms such as **must** and **must not** are testable. Public tests cover only
representative cases.

## R1 — record ownership and identity

- `LogRecord` has a non-negative offset and timestamp, an optional key, and a
  required value.
- Constructors and accessors must defensively copy arrays. Equality and hash
  code compare byte content, not array identity.
- `maxRecordBytes` limits the combined key and value byte count; a null key
  contributes zero bytes. A value alone, or a non-null key plus value, above
  that limit must be rejected before any file is changed.

## R2 — framed encoding

- A persisted frame is big-endian and contains, in order: a signed four-byte
  length `L`, the four-byte bitwise complement `~L`, a four-byte CRC32, then a
  body containing the marker, version, flags, offset, timestamp, key length,
  value length, key bytes when present, and value bytes. `L` counts the CRC32
  and body, but not the two length fields. The CRC32 covers the body only.
- The fixed body is 32 bytes. Marker `0x4d4c4f47`, version `1`, and flag bit
  `0x0001` mean MiniLog, format version one, and null key respectively. The
  only known flag is the null-key bit. A null key has length `-1`; a non-null
  empty key has length zero. Thus the encoded size is `44 + keyBytes +
  valueBytes`, and a valid `L` is from 36 through `36 + maxRecordBytes`.
- Decoding must distinguish clean end-of-file, an incomplete final frame, and
  a complete but invalid/corrupt frame.
- At a frame boundary, zero remaining bytes is clean EOF. One through seven
  remaining bytes is an incomplete header. With a complete eight-byte length
  header, a complement mismatch or out-of-range `L` is corruption; a valid
  header with fewer than `8 + L` bytes remaining is incomplete. Any invalid
  complete declared frame is corruption.
- Negative lengths, integer overflow, unknown marker/version/flags,
  inconsistent null flags or key lengths, negative value lengths, CRC
  mismatch, payload/frame disagreement, and over-limit frames are corruption,
  not records.

## R3 — segmented durable log

- `SegmentedLog.open` creates a missing data directory and an initial segment.
  Segment names use exactly 20 ASCII decimal digits for the base offset,
  followed by `.log`, independent of the process locale.
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

- Constructing a `PartitionLeader` must atomically claim exclusive mutation
  ownership of its supplied log and replication tracker. Their end offsets
  must match while that ownership is held. A failed construction releases any
  ownership it acquired and changes neither component nor durable bytes.
- Until the partition closes, mutations through a caller's retained
  `SegmentedLog` or `ReplicationTracker` alias must fail with
  `IllegalStateException` before mutation. Reads and snapshots may inspect
  state. Partition close closes its log and releases its tracker.
- An append with the active leader term writes exactly one record, then updates
  leader progress. It must verify component alignment before writing. An
  append with any other term is rejected before mutation.
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
- Public APIs use these stable outcomes:

  | Condition | Outcome |
  | --- | --- |
  | Required reference is null | `NullPointerException` |
  | Invalid caller scalar, record metadata, payload limit, membership, unknown replica, or read bound | `IllegalArgumentException` |
  | Partition append carries a term other than the active leader term | `FencedLeaderException` (`IllegalStateException`) |
  | Acknowledgement carries a future leader term | `IllegalStateException` |
  | Direct component mutation while that component belongs to a partition | `IllegalStateException` |
  | Log operation follows close or a reported write failure | `IllegalStateException` |
  | Complete invalid durable bytes, invalid segment structure, or incomplete non-final segment | `CorruptLogException` (`IOException`) |
  | Other storage failure | `IOException` |

- A stale-term acknowledgement returns `STALE_TERM` without mutation. A
  regressing current-term position may refresh that replica's last-contact
  time but returns `STALE_POSITION` without regressing its end offset or the
  watermark. An election denial returns a `VoteDecision`; these expected
  protocol outcomes are not exceptions.
