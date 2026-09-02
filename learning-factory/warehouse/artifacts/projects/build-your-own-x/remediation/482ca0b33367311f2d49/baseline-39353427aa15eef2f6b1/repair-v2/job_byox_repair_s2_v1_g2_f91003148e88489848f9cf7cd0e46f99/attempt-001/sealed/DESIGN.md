# Reference design and question answers

This is evaluator-only solution material.

## Architecture

The reference separates five trust boundaries:

1. `paths.py` converts an archive string into a strict `PurePosixPath`, then resolves it structurally
   beneath an actual root while rejecting existing links.
2. `layer.py` reads every tar header, validates and retains each derived whiteout target, checks the
   lexical destination ancestry, and simulates existing tree type changes before creating or deleting
   anything. Whiteouts run first; directories and streamed regular files run second. Explicit chmods
   normalize destination, implicit-parent, declared-directory, and file modes independently of umask.
3. `image.py` hashes while copying each caller-owned layer into private staging, applies only those
   staged bytes, and hashes an ordered canonical descriptor. A per-content POSIX file lock serializes
   publication of the same object; SQLite atomically chooses competing tag claims, and a loser removes
   only a newly published digest that has no committed object row. The built tree is frozen, bound
   into a canonical manifest, fsynced, and published by rename; later copies recheck tree integrity.
4. `store.py` keeps tag bindings and container state in SQLite. An immediate write transaction makes
   start a serialized claim, while triggers enforce the transition graph against every caller.
5. `runner.py` validates inputs and executes one argv array in a new process group with file-backed,
   bounded logs in the selected scratch directory. Marker and UTF-8 overhead share the configured
   byte budget. `engine.py` guarantees that a claimed launch exception is recorded as `EXITED/125`.

The filesystem and SQLite operations do not form one atomic transaction. Image creation avoids most
of that problem by publishing content before registering a tag; unreferenced identical content is
safe to reuse after a crash. Container creation copies first and inserts second, so a crash can leave
an unreferenced snapshot directory. A production reconciler would identify it using durable ownership
metadata and an age/lease rule.

## Answers to the design questions

1. String prefixes confuse siblings (`/tmp/root-other` starts with `/tmp/root`) and representation
   (`..`, duplicate separators, case/drive behavior on other platforms). Structural normalization plus
   `Path.is_relative_to` compares components; checking link-bearing parents prevents resolution from
   changing the root.
2. The reference rejects every raw `..`, even when lexical normalization would return beneath the
   root. Strict rejection makes audit behavior independent of component cancellation and stops paths
   from acquiring a different meaning if a parent later becomes a link.
3. Applying a harmless first entry before discovering a later traversal, special node, duplicate,
   quota violation, link-bearing destination ancestor, or impossible existing-tree type leaves
   evidence and can destroy lower-layer data through whiteouts. Header and destination simulation
   ensure those deterministic rejections have no destination side effect.
4. The reference processes all whiteouts first and ordinary files afterward, so `.wh.note` removes
   the lower `note` and the new `note` is present. The ordering is explicit and privately tested.
5. Each tar is hashed in the same pass that copies it to private staging, and only staging is later
   applied. A canonical schema-1 JSON descriptor commits to the ordered digest tuple. A tag does not
   participate: tags are names bound by the store, while identical content should share an object.
6. Tags store the same snapshot path. Publication clears every write bit and the manifest binds a
   canonical materialized-tree digest; create recomputes it before making a normalized writable copy.
   This detects ordinary and deliberate same-user changes, though it is not a hostile OS-identity
   boundary. Production would use a read-only lower mount and copy-on-write upper layer instead.
7. User-facing state checks belong in application code for clear errors. The transition graph also
   belongs in a trigger so another connection, a future code path, or a programming error cannot
   bypass it. Initial state is trigger-enforced too.
8. Two deferred transactions can both read `CREATED` before either updates. Later lock acquisition is
   awkward and application behavior can depend on timing. `BEGIN IMMEDIATE` acquires the write
   reservation before the read; the guarded update is an additional check.
9. Persist an execution attempt/lease row before launch with owner ID, generation, and expiry; after
   launch record PID identity or supervisor handle and an acknowledgement. Reconciliation can then
   distinguish an expired unacknowledged lease from a live supervised execution without trusting a
   worker's prose.
10. `communicate()` accumulates pipe output in memory. A timeout bounds elapsed time, not bytes emitted
    before that deadline. The reference sends output to temporary files in an explicit directory and
    reads only limit+1 bytes from each after termination. Retained content, UTF-8 replacement, and a
    size-dependent visible marker all share the returned-string byte budget.
11. A new session makes the child a process-group leader, allowing timeout cleanup to signal the
    group. It does not isolate filesystem paths, PIDs, users, networking, syscalls, CPU, memory, or
    credentials.
12. The host root, devices allowed to the current user, network, process namespace, IPC, CPU, memory,
    and inherited kernel identity remain available. A controlled environment also cannot prevent the
    program from reconstructing values or using absolute paths.
13. A hardened Linux launcher generally creates a user namespace and writes validated ID mappings,
    creates other namespaces, makes mount propagation private, constructs and switches to a sealed
    root, mounts `/proc` in the new PID namespace, establishes stdio and cgroups, drops groups,
    capabilities and securebits, sets no-new-privileges, applies seccomp, then execs. Exact ordering and
    privilege requirements are kernel/policy-specific and require a small reviewed native supervisor;
    this Python baseline deliberately does none of it.
14. Cleanup must resolve a durable object ID to an exact runtime-owned path and verify type, ownership,
    mount identity, and lease state. It should refuse links and unexpected mounts. Removing “all old
    directories matching a prefix” is not proof of ownership.
15. Passing local tests supports a narrow claim that the specified examples behaved under the named
    interpreter. Archive safety needs adversarial review; race behavior needs multi-process tests;
    sandbox claims require an isolated hostile environment and kernel-specific security review;
    production readiness requires operations, upgrades, recovery, monitoring, and transfer evidence.

## Invariants carried by code

- No tar payload is copied before all headers are accepted.
- No whiteout runs before deterministic destination ancestry and type conflicts are accepted.
- Layer digests and layer application consume one privately staged byte stream.
- Only regular files and real directories enter a rootfs.
- Ordered content, not a name, determines an image object; published content is reverified on use.
- Each persisted container begins at `CREATED` and follows the database transition graph.
- Exactly one successful claim can move one ID to `RUNNING`.
- A completed `start` call leaves either a domain error before claim or an `EXITED` record after claim.
- Captured output uses bounded reads; the truncation marker remains inside the byte bound.

These invariants do not imply containment of a hostile command.
