# Code-review answer key

1. Blocking correctness issue. Hash iteration does not implement lowest-ID
   election. With input [10, 4, 7], fail 4 and require 7. Select an explicit
   numeric minimum or retain sorted state.
2. Blocking atomicity issue. Quorum loss would leave an uncommitted leader entry,
   consume an offset, and make rejection observable. Validate all expected
   failures before any log mutation.
3. Blocking encapsulation issue. An unmodifiable view prevents caller writes but
   still changes when the backing ISR changes, so it is not a stable snapshot.
   Copy first, then optionally wrap the copy.
4. Blocking safety issue. The recovering replica could acknowledge or lead
   without the committed prefix. Add it only after catch-up and verification.
5. Latent safety issue. The current synchronous invariant keeps leader end equal
   to watermark, but the method contract is commitment-based and future
   asynchronous storage would leak a suffix. Cap reads at the watermark now.
6. Critical data-loss issue. A stale recovered copy cannot redefine acknowledged
   history. Preserve the watermark and remain leaderless until a replica
   containing the committed prefix becomes available.
7. Blocking ownership issue. Caller discipline is not enforceable and contradicts
   the API. Keep copies unless the API is redesigned around an actually immutable
   buffer with explicit lifetime rules.

Separate machines additionally require at least terms/epochs with durable votes,
quorum-intersecting election and commit rules, leader fencing, log matching and
conflict repair, failure detection/timeouts, retransmission, and durable metadata.
Minimum ISR plus “lowest ID” supplies none of those mechanisms.

No proposed change was applied; this file is an evaluation rubric.

