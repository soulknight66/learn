# Adversarial exercise answer key

Keep this file sealed from learners.

## Scenario oracles

Ownership passes only if every reread retains the bytes present at append time.
The original append buffer, a prior value result, and a prior result list must
all be powerless to alter later observations.

For local reads, the valid start range is zero through endOffset inclusive. For
replicated reads it is zero through highWatermark inclusive. A start at the
exclusive end or a zero limit is empty; a start beyond it or a negative argument
raises IllegalArgumentException.

For the rejected-write case, capture state after the failures and before append.
The watermark, leader (if one exists), ISR, availability, and every replica end
must be identical after the expected IllegalStateException. The rejected payload
must not consume an offset; after quorum is restored, the next successful append
uses the old watermark.

With IDs [9, 2, 6], initial leader is 2. After failing 2, leader is 6; after
failing 6, leader is 9 if it remains eligible. Caller order is irrelevant.

A discriminating stale-first trace is:

1. create replicas [1, 2, 3] with minimum ISR 2;
2. append A;
3. fail 3, then append B;
4. fail 1 and 2, leaving watermark 2 and replica 3 at end 1;
5. recover 3: it becomes available but cannot lead or join ISR;
6. recover 2: its end reaches watermark, so it may lead;
7. the now-safe leader repairs available replica 3 before it joins ISR.

At every point, reads either return exactly committed [A, B] through a leader or
fail because no leader can serve them. No operation may lower watermark 2.

The state-machine oracle should treat each accepted append as adding one cloned
byte string at the old watermark to every current ISR replica, then increasing
the watermark. Failure removes availability and ISR membership; recovery joins
only after its committed prefix matches. Invalid/rejected commands leave state
unchanged. Shrink failures by deleting command ranges, then individual commands,
while preserving the mismatch.

No adversarial suite was executed on the generation host because a JDK was not
available. These are expected oracles, not observed pass results.

