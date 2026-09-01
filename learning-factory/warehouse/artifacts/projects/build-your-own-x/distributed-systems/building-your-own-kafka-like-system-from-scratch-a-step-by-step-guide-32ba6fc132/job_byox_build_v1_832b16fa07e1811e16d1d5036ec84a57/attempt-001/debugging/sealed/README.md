# Debugging answer key

## Case A

The quorum/leader/alignment checks occurred after mutating a local log, or rollback
changed only the watermark. Preflight all ordinary failure conditions before the
first replica append. The regression snapshots all replica ends and watermark,
expects rejection, restores quorum, and verifies reuse of the old watermark as
the next offset.

## Case B

The watermark was treated as inclusive or the read limit failed to cap against
highWatermark minus fromOffset. Committed offsets occupy
[0, highWatermark). Compute the remaining committed count and pass no larger
limit to the leader log. Test starts at watermark minus one and separately at
watermark.

## Case C

Election iterated the caller's list or a hash set. Eligibility and selection are
separate: filter to available in-sync replicas containing the committed prefix,
then choose the numeric minimum. A sorted map/set or explicit minimum gives a
stable result.

## Case D

Recovery added ISR membership when availability changed. Availability may be set
before copying, but ISR membership must be the last step after prefix comparison,
ordered catch-up, and an end-equals-watermark check. Election must independently
require both availability and ISR eligibility.

## Case E

The implementation retained an input array or returned an internal array.
LogRecord must clone on construction and on every value access. Replicated append
should also snapshot once before visiting followers. Regression tests mutate both
the original and returned arrays.

## Case F

Recovery only attempted election on the first recovered node, or an early return
treated “available” as “fully recovered.” Every recovery with no leader must
reconsider whether that replica ends exactly at the watermark. Once a safe leader is
elected, repair other available laggards before adding them to ISR. Repeating
recover on an available but out-of-sync node must be allowed to make progress.

These diagnoses are reference expectations, not evidence that mutations were
compiled or tested on this host.
