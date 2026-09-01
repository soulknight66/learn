# SharedPageSystem design

## State model and synchronization

`SharedPageSystem` owns one mutex and four pieces of state:

- `processes: dict[int, Process]`, where each `Process` has
  `mappings: dict[int, PTE]` indexed by VPN.
- `segments: dict[str, int]`, mapping a live segment name to its frame ID.
- `frames: dict[int, Frame]`.
- `next_frame_id: int`, a monotonically increasing allocator. IDs are never reused, which makes
  an ID stable and avoids an ABA-style ambiguity in successive `stats()` snapshots.

A `PTE` contains a frame ID, a mode (`PRIVATE` or `NAMED_SHARED`), and a `writable` bit. A private
allocation is writable. A named mapping records the `writable` argument given to `map_shared`.
Fork copies all three fields.

A `Frame` contains exactly `PAGE_SIZE` bytes in a `bytearray`, plus two reciprocal owner sets:

- `mapping_owners: set[tuple[int, int]]`, containing one `(pid, vpn)` for each PTE that points to
  the frame;
- `name_owners: set[str]`, containing each live name that points to the frame.

The implementation derives `mapping_refs` and `name_refs` from the sizes of these sets rather than
maintaining independent counters. This makes a duplicate decrement, a missing increment, and the
specific leaked owner observable. One undifferentiated count would also lose the distinction
between a persistent name and a process mapping, even though unlink and unmap remove different
edges.

Every public operation, including validation and `stats()`, runs while holding the same mutex.
Internal helpers have an `_locked` suffix and are called only with that mutex held, so they never
reacquire it. Thus each call is linearizable as one operation, and no observer can see the
temporary ordering used to update reciprocal structures. Expected validation errors are detected
before the commit portion of a call, leaving state unchanged.

New frames are zero-filled, then the supplied initial bytes are copied at offset zero. Frame
allocation, publication, owner changes, page-table changes, and possible reclamation all occur
inside the mutex. `_reclaim_if_unowned_locked(frame_id)` deletes a frame if and only if both owner
sets are empty.

## Representation invariants

The following conditions hold before and after every public method:

1. For every `processes[pid].mappings[vpn] = pte`, `pte.frame_id` is live and
   `(pid, vpn)` occurs exactly once in that frame's `mapping_owners`.
2. Conversely, every `(pid, vpn)` in a frame's `mapping_owners` resolves to exactly one PTE whose
   frame ID is that frame. Therefore every PTE contributes exactly one mapping reference.
3. For every `segments[name] = frame_id`, the frame is live and contains `name` in
   `name_owners`; every name owner has the reciprocal `segments` entry.
4. A frame is present exactly while it has at least one mapping owner or at least one name owner.
   In particular, a named but unmapped frame and an unlinked but still-mapped frame remain live.
5. A frame reached from a `PRIVATE` PTE has no name owners and no `NAMED_SHARED` PTEs. Private
   frames become multiply mapped only through fork. A frame created for a named segment has only
   `NAMED_SHARED` PTEs, even after its name is unlinked.
6. Writes through `NAMED_SHARED` PTEs never clone. Writes through `PRIVATE` PTEs clone exactly
   when another mapping owner remains on the old frame. A lingering “COW” flag is unnecessary:
   private mode plus the current mapping-owner set supplies the complete decision.
7. A read-only PTE is never modified by `write`, and fork preserves its permission.
8. A `(pid, vpn)` and a segment name are each unique in their respective dictionaries. All frame
   IDs are distinct and less than `next_frame_id`.
9. Each successful teardown removes every affected ownership edge once. Failed calls remove none.

An internal invariant checker used by tests can walk all three dictionaries in both directions,
recompute both owner sets, verify mode separation, and reject an ownerless live frame.

## Operation algorithms

### Creation and mapping

`create_process(pid)` rejects an existing PID with `ValueError`; otherwise it installs an empty
mapping table.

`alloc_private(pid, vpn, initial)` first requires a known process, an absent VPN, and at most one
page of initial content. It allocates a zero-filled frame, installs a writable `PRIVATE` PTE, and
adds `(pid, vpn)` to the frame's mapping owners. The frame has no name owner.

`create_shared(name, initial)` rejects a duplicate name and oversized content. It allocates a
zero-filled frame, installs `segments[name]`, and adds the reciprocal name owner. It creates no
process mapping.

`map_shared(pid, vpn, name, writable=...)` requires an existing process and name and an unused VPN.
It installs a `NAMED_SHARED` PTE for the segment frame with the requested permission and adds its
mapping owner. An unlinked name is absent from `segments`, so it cannot be used for a new mapping.

### Read and write

`read(pid, vpn, length, offset=0)` looks up the process and PTE and validates
`length >= 0`, `offset >= 0`, and `offset + length <= PAGE_SIZE`. It returns an immutable `bytes`
copy of that slice. `offset == PAGE_SIZE` is valid only for a zero-length access.

`write(pid, vpn, data, offset=0)` looks up the process and PTE, validates
`offset >= 0` and `offset + len(data) <= PAGE_SIZE`, and rejects a read-only PTE with `ValueError`.
A zero-length write is a successful no-op and does not cause a COW allocation.

For a writable `NAMED_SHARED` PTE, write modifies the existing frame in place. All mappings of that
frame therefore observe the bytes.

For a `PRIVATE` PTE:

- If its frame has one mapping owner, no other mapping can observe it, so write safely modifies
  that frame in place.
- If it has more than one mapping owner, write allocates a full-page copy. The caller's PTE and
  reciprocal owner edge move to the new frame, its edge is removed from the old frame, and only
  then is the requested slice changed in the new frame. Other mappings retain the old bytes.

The clone test deliberately uses only mapping owners, not name owners or a stale cached count.

### Fork and teardown

`fork(parent_pid, child_pid)` requires a known parent and an unused child PID. It constructs a
child mapping table with one copied PTE per parent PTE and adds `(child_pid, vpn)` to every
corresponding frame. Private PTEs now obtain COW behavior from having multiple mapping owners;
named PTEs continue to point to the same intentionally shared frames. No frame bytes are copied by
fork.

`unmap(pid, vpn)` removes that PTE and exactly its reciprocal mapping owner, then calls the
reclamation helper. It raises `KeyError` for either an unknown process or an unmapped VPN.

`exec(pid)` keeps the process entry but atomically drops every old PTE. For each saved mapping it
removes the matching owner once, clears the mapping table, and reclaims newly ownerless frames.
The process is left with an empty address space.

`exit(pid)` performs the same complete mapping teardown, then removes the process entry. It raises
`KeyError` for an unknown PID.

`unlink_shared(name)` removes the segment dictionary entry and reciprocal name owner, then
reclaims the frame only if it has no mappings. Existing PTEs contain frame IDs rather than names,
so their reads and writes remain valid. A later `map_shared` using the removed name raises
`KeyError`.

`stats()` takes the mutex and returns a fresh snapshot. `process_count`, `frame_count`, and
`segment_count` are dictionary sizes. `frames` contains every live frame ID and fresh dictionaries
whose `mapping_refs` and `name_refs` are the corresponding owner-set sizes. No mutable internal
object escapes.

## Lifecycle traces

### Private allocation, fork, COW write, and exit

Assume parent `P` allocates VPN 4 with bytes `A`:

| Event | Process mappings | Frame owners and contents | Name owners |
|---|---|---|---|
| allocate | `P:4 -> F0 PRIVATE` | `F0: {(P,4)}, A` | none |
| fork to `C` | `P:4 -> F0`; `C:4 -> F0` | `F0: {(P,4),(C,4)}, A` | none |
| `C` writes `B` | `P:4 -> F0`; `C:4 -> F1` | `F0: {(P,4)}, A`; `F1: {(C,4)}, B` | none |
| `P` exits | `C:4 -> F1` | `F0` reclaimed; `F1: {(C,4)}, B` | none |

The child write clones because another mapping still refers to `F0`. If the parent had exited
before the child write, the child's mapping would be the only owner and the child would reuse
`F0` rather than allocate a needless copy.

### Create, two maps, unlink, and unmap

Assume name `S` is created and processes `P` and `Q` map it:

| Event | Process mappings | Frame mapping owners | Frame name owners |
|---|---|---|---|
| create `S` | none | `F2: {}` | `F2: {S}` |
| map twice | `P:8 -> F2`; `Q:9 -> F2` | `F2: {(P,8),(Q,9)}` | `F2: {S}` |
| unlink `S` | mappings unchanged | `F2: {(P,8),(Q,9)}` | `F2: {}` |
| unmap `P:8` | `Q:9 -> F2` | `F2: {(Q,9)}` | `F2: {}` |
| unmap `Q:9` | none | `F2` reclaimed | none |

A write through either mapping before its unmap is visible through the other, including after
unlink.

## Concurrency hazards and linearized outcomes

The single mutex covers every lookup/check followed by modification; using a lock only around the
final dictionary assignment would leave lifetime edges exposed. Important races are:

- **Two post-fork private writers:** the first serialized writer sees two owners and clones. The
  second sees one owner on its old frame and reuses it. Both finish with different frames and their
  own bytes; no frame is lost and no unnecessary second clone occurs.
- **Map versus unlink:** if map linearizes first, it acquires a mapping edge and unlink removes only
  the name edge, so the mapping survives. If unlink linearizes first, map gets `KeyError`. There is
  no outcome in which map succeeds with a reclaimed frame.
- **Fork versus private write:** if fork is first, the write sees an additional mapping and clones;
  if write is first, the child inherits the already-written frame. Both orders match a sequential
  history.
- **Fork versus exec/exit/unmap:** the lock prevents fork from copying a PTE while teardown is
  removing its owner. Fork either copies the complete pre-teardown address space or observes the
  complete post-operation state (or an absent parent after exit).
- **Read/write versus teardown:** an access either completes against a live PTE before teardown or
  looks up afterward and raises `KeyError`. Reclamation cannot occur during the access.
- **Concurrent shared writes:** each whole method call is serialized, so overlapping bytes follow
  the later linearized call and cannot be torn at method granularity.
- **Duplicate creation/mapping:** the duplicate check and insertion are one critical section, so
  exactly one contender succeeds and the other gets `ValueError`.
- **Stats versus mutation:** stats sees one complete state, never a PTE without its reciprocal
  owner or counts from different moments.

The same critical section must cover frame-ID allocation, cloning and PTE redirection, reciprocal
owner updates, bulk teardown, unlink, and the final reclaim decision. These are all check-then-act
sequences where splitting locks could lose an ownership edge or reclaim a still-reachable frame.

## Failure behavior

All documented errors are explicit and leave counts, bytes, mappings, and the frame-ID allocator
unchanged:

- `ValueError`: duplicate PID, duplicate name, duplicate `(pid, vpn)`, initial data larger than
  `PAGE_SIZE`, negative/out-of-page read length or offset, out-of-page write range, or write through
  a read-only mapping.
- `KeyError`: unknown PID where a process is required, unknown parent, unknown segment name,
  unmapped VPN, unlink of an unknown/already-unlinked name, or exit/exec of an unknown process.

For deterministic handling when more than one input is bad, an operation first resolves the state
objects it needs in signature order (process, then VPN or name), then checks access bounds, then
checks write permission. Creation methods check their duplicate key before content size. This
precedence is an implementation choice because the contract fixes each individual error class but
does not specify combined-invalid-input precedence.

Internal consistency failures are programming bugs, not user errors; test builds use assertions in
the invariant checker rather than translating them into one of the public exceptions.

## Deterministic test plan

Tests use `unittest`, public calls, byte-exact assertions, and `stats()` snapshots. Tests that need
deeper validation invoke the internal invariant checker after each step.

1. **Creation and validation:** create distinct processes and segments; verify all three counts,
   zero padding, and owner counts. Check every duplicate, unknown object, oversized initial value,
   negative range, boundary-crossing range, and missing VPN. Snapshot state before each rejected
   call and assert it is unchanged afterward.
2. **Boundary accesses:** exercise offsets 0 and 4095, full-page access, `(4096, 0)`, empty initial
   content, a zero-length write, and every one-byte-over-boundary case. Verify returned values are
   immutable `bytes`.
3. **Basic private COW:** allocate a patterned page, fork, and check one frame with two mapping
   refs. Write in the child and verify the parent retains the old page, the child has the changed
   page, and stats shows two one-owner frames. Write the parent afterward and verify frame count
   stays two.
4. **Repeated fork and last-owner reuse:** fork parent to two children, write one child and expect
   one clone plus a two-owner old frame; exit one old-frame owner, then write the last old-frame
   owner and verify no new frame appears. Also fork from a child after it has cloned.
5. **Named sharing:** map one segment writable into unrelated processes at different VPNs. Write
   from each and verify both see the changes and stats retains one frame. Fork one mapper and
   verify parent, child, and unrelated process still share that frame.
6. **Permissions:** create writable and read-only mappings of the same named frame. Verify the
   read-only mapping observes others' writes but its own write raises `ValueError` without changing
   data. Fork it and verify the child remains read-only.
7. **Unlink lifetime:** test a named but unmapped frame, then the full create/map/map/unlink/unmap/
   unmap trace. After unlink, reject new maps but preserve access through old mappings. Verify the
   frame disappears only after the final mapping. Separately, unlink an unmapped segment and expect
   immediate reclamation.
8. **Exec, exit, and mixed mappings:** give a process several private mappings and several named
   mappings also held elsewhere. `exec` must leave the process present and empty while releasing
   each edge once; `exit` must additionally remove it. Verify shared/name-owned frames survive and
   solely owned private frames do not. Repeating unmap/exec/exit through invalid paths must raise
   rather than double-decrement.
9. **Stable stats:** retain one frame across several snapshots and confirm its ID stays fixed.
   Reclaim it, allocate another, and confirm the old ID is not reused. Mutating a returned stats
   dictionary must not alter system state.
10. **Concurrent duplicate race:** release two threads from a `Barrier` to allocate the same VPN
    (and, separately, create the same name). Join with bounded timeouts. Assert one success, one
    `ValueError`, one resulting object, and valid reciprocal owners; do not depend on which thread
    wins.
11. **Concurrent COW writers:** fork one private mapping, use a barrier to start distinct full-page
    writes in parent and child, and join with timeouts. Each process must contain its own complete
    pattern, stats must show two frames with one owner each, and the invariant checker must pass.
12. **Map/unlink and access/exit races:** synchronize starts but accept only the two legal
    serialized histories described above. Assert final lifetime/count invariants for either winner.
    For a full-page shared-write race, the final bytes must equal one complete writer pattern, never
    a mixture.
13. **Stress sequence:** use a fixed seed to generate legal alloc/map/fork/write/unmap/exec/unlink/
    exit operations against a small reference model. After every operation compare reads and stats
    and run the reciprocal-owner checker. Concurrent batches use barriers and assert a result set
    compatible with some serialized order rather than relying on timing.

Every thread is joined with a bounded timeout so a lock leak or deadlock becomes a deterministic
test failure instead of a hung suite.
