# Reference design

The shared core separates byte-stream parsing, application semantics, response serialization,
and connection handling. The reference server owns a fixed worker set and bounded queue. The
acceptor either enqueues a socket or immediately returns 503; each worker owns exactly one
socket at a time and always completes its queue accounting. A stop event, listener close,
pending-socket drain, sentinels, and bounded joins make lifecycle ownership explicit.

The application serializes mutations under one re-entrant lock. This is deliberately simple:
it prevents lost updates and protects the LRU idempotency map, but constrains throughput. The
parser rejects transfer coding and duplicate headers rather than implementing ambiguous
combinations. Tight feature scope is a security and teaching choice, not full HTTP compliance.
