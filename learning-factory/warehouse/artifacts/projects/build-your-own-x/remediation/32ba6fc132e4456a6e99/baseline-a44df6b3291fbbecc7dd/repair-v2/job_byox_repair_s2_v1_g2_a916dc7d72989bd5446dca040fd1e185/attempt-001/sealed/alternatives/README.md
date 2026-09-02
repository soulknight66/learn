# Sealed alternatives

Several valid solutions can satisfy the public API:

- Keep a sparse `(offset, filePosition)` index instead of all decoded records in
  memory. This improves heap use but adds index recovery and consistency rules.
- Store a checksummed fixed-size header plus checksummed payload. That resolves
  more length-prefix ambiguity at the cost of format overhead.
- Return immutable `ByteBuffer` views instead of copied arrays. This can reduce
  copies, but ownership becomes subtle when buffers or mapped segments close.
- Represent follower progress in a persistent event log and rebuild the tracker
  after restart. This improves auditability but requires term-bound snapshot and
  compaction rules.
- Use five replicas rather than three. Two failures can be tolerated for
  commitment, while write latency and storage/network cost increase.

An alternative is acceptable only if it preserves the behavioral contract;
matching the sealed implementation's private structure is neither required nor
desirable.
