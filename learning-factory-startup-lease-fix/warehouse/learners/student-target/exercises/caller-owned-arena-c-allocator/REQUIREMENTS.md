# Allocator contract

Implement the API in `include/allocator.h` over only the supplied arena. The allocator must
return pointers aligned for `max_align_t`, reject size-rounding overflow, split reusable free
space, coalesce physical neighbors, preserve the old prefix on successful resize, and leave
the original allocation unchanged when resize fails. Zero-size allocation returns `NULL`;
freeing `NULL` succeeds. An immediate second free of a block still present in the physical
list returns `LF_ERR_DOUBLE_FREE`. Once coalescing removes that block identity, the stale
pointer returns `LF_ERR_INVALID_POINTER`; this bounded design does not retain tombstones.

The caller owns disjoint storage returned by `malloc`/`aligned_alloc` (or equivalent storage
with no incompatible declared object type): a `max_align_t`-aligned state region of at least
`lf_state_size()` bytes and an arena span whose start may be unaligned within its allocation.
Initialization rejects overlapping spans, may align the arena start inward, and must never
access bytes outside it. A declared character array remains a character array in portable C;
alignment and a cast do not change its effective type. Such stack/static backing is outside
this reference contract. The caller/harness may acquire storage, but allocator implementations
may not call `malloc`, `calloc`, `realloc`, `free`, `sbrk`, or `mmap` themselves. `lf_check`
validates physical coverage and core list invariants; `lf_get_stats` reports aligned capacity,
not caller's unrounded request sizes.

This API is deliberately single-threaded, fixed-capacity, and non-interposing. It has no
concurrent ownership protocol, OS page acquisition/return, hardened metadata, guard pages,
quarantine, per-thread caches, ABI compatibility, or latency guarantee. Those omissions make
every result `PARTIAL` and `NOT_PRODUCTION_READY`.

Definition of done requires strict C11 compilation, public and withheld contracts,
deterministic randomized model/data-integrity testing, optional sanitizer execution only
after runtime detection, actual benchmark output with raw values/environment, and honest
limitation documentation. Learner-authored claims are not validation evidence.
