# Concepts behind MiniLog

## Offset spaces

A record offset names one entry; an end offset names the boundary after a
prefix. If a replica's end offset is 7, records 0 through 6 are present. Keeping
that distinction explicit avoids the classic off-by-one error in commit and
fetch logic.

## Frames and crash recovery

Files are byte streams, so recovery needs framing. A length and its bitwise
complement establish a candidate boundary without trusting one unprotected
integer; a body checksum then says whether the complete candidate retained its
contents. An incomplete suffix can result from a crash during append. A
complete header-integrity or checksum failure is evidence of corruption and
should not be silently discarded.

## Replication versus consensus

Replication copies bytes. Consensus decides which history is authoritative.
MiniLog separates those concerns: election terms fence stale leaders, voting
prefers sufficiently fresh logs, and a fixed majority determines committed
prefixes. This model does not claim to be a complete consensus protocol.

## High watermark

The high watermark is an end offset. Records below it survived on a majority
according to the model and are visible to committed readers. A leader can have
newer local records above it; those are visible only under leader isolation.

## Monotonic state

Terms, replica end offsets, the next local offset, and the high watermark only
move forward within their defined lifetime. Checking monotonicity near every
state change makes stale messages and impossible histories fail locally.

## Fault model

The exercise models fail-stop replicas, delayed/duplicated acknowledgements,
stale-term messages, torn final writes, and detected bit corruption. It does
not model Byzantine replicas, filesystem lies, network protocols, or atomic
membership reconfiguration.
