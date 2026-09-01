# Review answer: shared-count IRQ queue

The producer advances `head` before writing, while an initially empty queue normally has both indices
at the first slot; its first event lands in the next slot but pop reads the original slot. Pick one
convention—head as next write is simplest—and write before advancing it.

The shared count has two writers. Foreground can load count for `--count`, be interrupted, let push
load/increment/store count, then resume and store its stale decrement result, erasing the producer's
update. `volatile` neither makes the read-modify-write atomic nor publishes the event before metadata.

Use producer-owned head, consumer-owned tail, and reserve one slot. Producer reads tail with acquire,
writes the event, then release-stores head. Consumer acquire-loads head, reads the event, then
release-stores tail. For this challenge, reject a full push, preserve queued events, and increment a
drop counter. A broader SMP design still needs a platform memory-model review.
