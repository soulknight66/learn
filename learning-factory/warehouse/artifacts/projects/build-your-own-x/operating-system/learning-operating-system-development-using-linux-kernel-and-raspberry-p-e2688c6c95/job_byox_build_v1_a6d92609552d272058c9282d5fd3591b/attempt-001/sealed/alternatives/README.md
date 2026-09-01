# Sealed alternative implementations

Three extensions were considered but intentionally not made the reference contract:

- **Eager fork:** allocate and copy every writable frame during fork. This simplifies writes but makes fork itself capacity-sensitive and obscures copy-on-write invariants.
- **Shared open descriptions:** introduce a table between descriptors and files so forked descriptors share cursors. This is closer to POSIX but adds a third independently counted resource.
- **Generation handles:** encode a slot and generation in process/file handles. This prevents stale references without consuming monotonically increasing global IDs, but makes the introductory API less direct.

A useful advanced branch can implement one alternative while preserving the public behavior behind an adapter, then compare state size, number of transactional failure points, and invariant complexity. No measured performance claim is included.
