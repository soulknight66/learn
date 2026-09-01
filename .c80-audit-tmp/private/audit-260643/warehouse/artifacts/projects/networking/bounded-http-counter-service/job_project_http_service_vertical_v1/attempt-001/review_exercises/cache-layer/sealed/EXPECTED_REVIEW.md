# Expected review

## Critical: cache key crosses authorization principals

The key is only `request.target`. A response for authenticated Alice at `/v1/me` is returned
to Bob. Either do not cache personalized data or include a verified authorization/tenant and
representation context in a carefully specified key. The sealed demonstration reproduces the
disclosure.

## Major: no invalidation or freshness contract

Successful GETs live forever and mutations do not invalidate them, so clients can observe
stale state indefinitely. Define cacheable routes, validators/versions, TTL, and mutation
invalidation based on application semantics.

## Major: unbounded memory controlled by request targets

Every distinct query string/path can add an entry. Add canonicalization, a hard capacity,
eviction metrics, and admission rules; account for response body size, not only entry count.

## Major: application work occurs under the global cache lock

A slow miss serializes every cached GET and turns one backend stall into head-of-line blocking.
Use a bounded single-flight design per key or call the backend outside the global metadata lock
while accepting/documenting duplicate fills.

## Minor: no cache outcome observability

Hit, miss, eviction, fill duration, and size signals are necessary to validate the claimed
latency improvement and spot churn. This is secondary to the correctness and security issues.
