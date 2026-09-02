# Sealed design rationale

This file answers the learner prompts and must not enter the learner view.

## Durable frame

The reference frame is big-endian. A four-byte length is immediately followed
by its four-byte bitwise complement. The length counts the following CRC and
body. Recovery validates the complete pair and configured bounds before using
the length to classify missing body bytes. A plausible single-field length bit
flip therefore cannot masquerade as a torn tail.

The CRC32 covers the body: marker, version, flags, offset, timestamp, key/value
lengths, and payload. The fixed body is 32 bytes. A null key uses both a flag
and length `-1`; non-null empty keys use length zero. The complement is compact
accidental-corruption detection, not authentication or protection from an
adversary able to rewrite multiple fields consistently.

## Recovery and segment invariants

Segment base offsets equal the next expected record offset. The first segment
therefore starts at zero, every record increments the expectation by one, and
the next segment's filename must equal that expectation. An empty segment is
allowed only at the end, representing a rotation or newly initialized log.

Recovery reads complete frames until clean EOF. It truncates at the last valid
boundary only when the decoder reports an incomplete frame in the final
segment. It never catches a general decode exception and calls it a torn tail.
That preserves checksum failures and impossible metadata as durable evidence.

Segment names use `Locale.ROOT`; discovery and creation therefore agree on the
same 20 ASCII digits regardless of the host's FORMAT locale.

Reads count full encoded frame bytes, including both length fields, because
this is deterministic and matches the resource consumed by replication. A
first record larger than the remaining budget is not returned. Rotation is
checked before append, but one valid frame may exceed the segment target when
the active segment is empty; otherwise a small target could make a valid
record impossible to store.

## Election state

Log freshness is lexicographic on `(lastLogTerm, lastOffset)`, with `(-1, -1)`
representing an empty log. A higher request term is observed before freshness
and prior-vote checks, clearing the old vote even when the candidate loses.
Repeating the same vote is idempotently granted. The reference state is only an
in-memory transition model; durable term/vote storage is a production gap.

## Replication state

Every progress value is an end offset. The leader moves its position only after
a complete local append. A follower acknowledgement can hold or advance its
position but cannot move it backward or beyond the leader. Old-term messages
return `STALE_TERM` without touching progress; future terms indicate this
leader is stale and fail explicitly.

For `N` fixed replicas, the watermark is the element at index
`floor(N/2)` after sorting end offsets descending. This is the greatest prefix
held by a strict majority. Since individual positions are monotonic, taking the
maximum with the previous watermark is defensive and preserves monotonicity.

The in-sync set is a health diagnostic computed from caller-supplied time,
record lag, and silence. It does not change membership or quorum size. Treating
a shrunken in-sync set as the voting universe could let different minorities
commit incompatible histories.

## Integrated mutation order

Construction claims mutation ownership of the log and replication tracker
with a private token, then checks their end offsets while both claims are held.
If the second claim or alignment check fails, construction releases every
claim it acquired. Public mutation methods reject calls through retained
aliases while ownership is active; partition-only package methods require the
unforgeable token. Read-only offset and snapshot methods remain available for
diagnostics. Closing the partition closes the log and releases the tracker.

`PartitionLeader.append` checks the expected term and rechecks component
alignment before asking the owned log to validate or encode the record. The
log validates immutable metadata and the payload limit before rotation or
write. Only a completed write advances its in-memory next offset; only then
does partition code advance owned leader progress. Because outside mutation is
blocked, no retained alias can interleave between those steps. If an I/O
operation reports failure, the log instance becomes unusable and a fresh
recovery pass must classify the bytes.

Committed fetches first perform the normal byte/count-bounded local read, then
retain only offsets below the watermark. This preserves the same budgets for
both isolation levels and cannot expose a later local suffix.

## Beyond the exercise

A networked broker also needs durable election metadata, replicated leader
epochs, follower conflict truncation, directory fsync, exclusive data locks,
request identity/idempotence, backpressure, authentication/authorization,
quotas, metadata consensus, observability, operational repair tools, and a
defined rolling-upgrade protocol. None is implied by passing these tests.
