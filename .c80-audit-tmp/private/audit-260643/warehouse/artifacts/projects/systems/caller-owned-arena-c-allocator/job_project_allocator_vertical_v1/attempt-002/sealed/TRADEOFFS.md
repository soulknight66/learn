# Tradeoffs and measurement questions

First-fit tends to stop searching early and preserve larger tail regions, but placement
depends strongly on history. Best-fit spends more search work hoping to leave larger regions;
its small remainders can be harmful. Segregated bins bound much candidate search in common
cases but cost larger headers, more state, and complex updates. The included benchmark emits
raw elapsed nanoseconds, operation counts, free-block layout, and external-fragmentation ratio
for one deterministic smoke workload. Treat it as a hypothesis probe, not a universal rank.
Profile repeated, warmed, workload-representative runs before changing an architecture.

The references place typed metadata directly in standard dynamically allocated storage. They
intentionally do not promise portable typed access over a declared `unsigned char[]`; alignment
alone cannot change that array's effective type. An extension for effective-type-safe
stack/static arenas should replace direct struct lvalues with an offset/byte representation and
`memcpy`-based metadata access (or expose a compatible storage type), then repeat all tests under
optimizing compilers. This is a known contract boundary, not a runtime-detected property.
