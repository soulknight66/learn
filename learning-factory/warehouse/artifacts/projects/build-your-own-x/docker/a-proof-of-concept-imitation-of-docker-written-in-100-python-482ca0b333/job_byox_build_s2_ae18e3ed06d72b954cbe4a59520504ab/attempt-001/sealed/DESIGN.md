# Reference design and question answers

This is evaluator-only solution material.

## Architecture

The reference separates five trust boundaries:

1. `paths.py` converts an archive string into a strict `PurePosixPath`, then resolves it structurally
   beneath an actual root while rejecting existing links.
2. `layer.py` reads every tar header and enforces quotas before creating the destination. Whiteouts
   run first; directories and streamed regular files run second. Modes and metadata are normalized.
3. `image.py` hashes the exact layer bytes, hashes an ordered canonical descriptor, builds beneath an
   unpredictable private directory, fsyncs a canonical manifest, and publishes with directory rename.
4. `store.py` keeps tag bindings and container state in SQLite. An immediate write transaction makes
   start a serialized claim, while triggers enforce the transition graph against every caller.
5. `runner.py` validates inputs and executes one argv array in a new process group with file-backed,
   bounded logs. `engine.py` guarantees that a claimed launch exception is recorded as `EXITED/125`.

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
3. Applying a harmless first entry before discovering a later traversal, special node, duplicate, or
   quota violation leaves evidence and can destroy lower-layer data through whiteouts. Header
   preflight ensures archive-format rejection has no destination side effect.
4. The reference processes all whiteouts first and ordinary files afterward, so `.wh.note` removes
   the lower `note` and the new `note` is present. The ordering is explicit and privately tested.
5. Each exact tar byte stream gets a SHA-256 digest. A canonical schema-1 JSON descriptor commits to
   the ordered digest tuple. A tag does not participate: tags are mutable-looking names bound by the
   store, while identical content should share an object.
6. Tags store the same immutable snapshot path. Container creation recursively copies only regular
   files and directories into a separate tree; it never gives the process the image path as cwd.
   Production would use a read-only lower mount and copy-on-write upper layer instead.
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
    before that deadline. The reference sends output to temporary files and reads only limit+1 bytes
    from each after termination.
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
- Only regular files and real directories enter a rootfs.
- Ordered content, not a name, determines an image object.
- Each persisted container begins at `CREATED` and follows the database transition graph.
- Exactly one successful claim can move one ID to `RUNNING`.
- A completed `start` call leaves either a domain error before claim or an `EXITED` record after claim.
- Captured output uses bounded reads; a truncation marker makes loss explicit.

These invariants do not imply containment of a hostile command.
