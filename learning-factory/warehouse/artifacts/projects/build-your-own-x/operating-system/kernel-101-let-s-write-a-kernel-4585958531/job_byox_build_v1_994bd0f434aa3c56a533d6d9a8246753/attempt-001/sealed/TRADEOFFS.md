# Reference tradeoffs

The implementation optimizes for inspectability and deterministic tests, not scale.

- One-byte-per-frame storage is wasteful compared with a bitmap, but every ownership transition is
  obvious. All allocations are linear in `TK_MAX_FRAMES`.
- A fixed process table avoids allocator failure inside scheduling. It cannot support arbitrary
  process counts, priorities, deadlines, CPU affinity, or multiple CPUs.
- The mapping array models page-table semantics without creating hardware page tables. Translation
  and duplicate detection are linear; there are no accessed/dirty bits or TLB invalidations.
- The RAM filesystem stores the full maximum payload in every slot. This makes failure atomicity
  simple at the cost of memory and excludes directories, links, sparse files, and persistence.
- Public structure layouts expose state to tests and teaching tools, but prevent internal
  representation changes without an API revision.

These choices are appropriate to a bounded state-machine exercise. They are not recommendations for
a production kernel.
