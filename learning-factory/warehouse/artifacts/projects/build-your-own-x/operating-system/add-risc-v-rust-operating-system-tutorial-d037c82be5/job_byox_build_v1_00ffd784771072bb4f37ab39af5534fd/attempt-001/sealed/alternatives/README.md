# Sealed alternatives

These are design alternatives, not additional validated implementations.

- A bitmap frame allocator uses one bit per frame and a rotating search hint.
  It has compact metadata and predictable storage but must carefully restore
  the hint/bit on transaction rollback.
- An intrusive scheduler stores queue links in process records, avoiding a
  second PID allocation. It requires stronger link ownership invariants and
  careful removal on every transition.
- A sparse filesystem stores `BTreeMap<block_index, Box<[u8; 4096]>>` per file.
  Holes cost no data blocks, but read/write must split ranges and roll back a
  group of block allocations.
- A typestate PTE wrapper can expose disjoint `Invalid`, `Branch`, and `Leaf`
  representations so reserved combinations cannot be constructed internally.
- Binding `Sv39<'a>` to `&'a mut FrameAllocator` prevents wrong-allocator calls
  statically, but makes composing several address spaces with one allocator
  awkward without interior mutability or an owning memory manager.

The chosen reference favors an explicit, small API whose failure effects are
easy to test. None of these alternatives has been benchmarked in this pack.
