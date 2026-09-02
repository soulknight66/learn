# Reference review

Review scope: generated Python implementation, public and private tests, learner/solution separation,
and documented claims. This is a local code review, not an independent production or security audit.

## Findings addressed in the reference

- Archive extraction is manual and header-first; no use of `extract()` or `extractall()` exists.
- Destination trees are rejected if they contain links or special files, avoiding lower-layer link
  pivots. The supplied ancestry is checked lexically before resolution, and a type-state simulation
  rejects deterministic whiteout/target failures before mutation. Derived deletion targets are
  grammar-checked and retained at header preflight, while destination and implicit directory modes
  are set explicitly rather than inherited from umask. Normalized duplicates and file-as-ancestor
  layouts are rejected.
- Per-file, member-count, and aggregate declared-byte quotas are enforced before mutation.
- Caller-owned layers are staged while hashing and only staged bytes are applied. Per-content POSIX
  locks serialize same-object publication; SQLite chooses competing tag claims, and a loser removes
  only its unreferenced publication. Failed builds are removed. Published modes are read-only and a
  manifest-bound tree digest is verified before copying.
- State transitions are checked by application logic and SQLite triggers. Start claims begin with
  `BEGIN IMMEDIATE` and use a state predicate on update.
- Subprocesses use argv, `shell=False`, explicit environment, new session, timeout, group kill, and
  file-backed bounded capture in an explicit directory. Marker-inclusive UTF-8 output stays within
  the configured byte limit.
- Student release is enforced by a checked exact-file allowlist and deterministic exporter. The
  learner-safe copying notice carries operative generated-material terms without exposing full
  evaluator provenance; the full evaluator pack is explicitly not a learner artifact.
- Engine launch exceptions are converted to durable exit evidence rather than leaving ordinary
  failures at `RUNNING`.

## Known high-severity limitation

The executed command is not sandboxed. `cwd`, environment filtering, and a process group do not stop
host filesystem, network, IPC, or resource access. This implementation must not execute untrusted
code and must not be advertised as a container security boundary.

## Known medium-severity gaps

- There is no lease/reconciler for a runtime crash after a successful claim.
- Temporary log files have no disk quota while the process is running.
- Decompression CPU and compressed input bytes are not externally budgeted.
- Publishing a directory and registering its tag are not one transaction; a crash may leave safe but
  unreferenced content.
- Snapshot creation and its database insert are not one transaction; a crash may leave an orphan.
- Image trees use read-only modes and same-user integrity checks, not read-only mounts or a separate
  OS identity; a hostile same-user process can race verification.
- SQLite schema evolution and forward/backward compatibility are not implemented.
- The CLI has no lock-owner diagnostics, garbage collection, signal forwarding, or interactive mode.

## Claim review

The generated repository truthfully reports `GENERATED` and `PARTIAL`. Passing observations in
`VALIDATION.md` are local evidence only. No benchmark, fuzz, namespace isolation, transfer,
productionization, or third-party security-review label is claimed.
