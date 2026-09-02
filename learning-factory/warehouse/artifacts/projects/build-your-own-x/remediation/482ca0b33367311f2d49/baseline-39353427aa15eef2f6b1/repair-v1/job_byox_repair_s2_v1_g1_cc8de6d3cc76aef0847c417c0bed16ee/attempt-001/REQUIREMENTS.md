# Requirements

Implement a Python 3.11 package named `pydocklet`. Only the standard library may be used. The terms
MUST, SHOULD, and MAY describe the learner contract.

## 0. Distribution boundary

The production pack is not a student repository. A learner view MUST be created from the exact-file
allowlist in `environment/student_view_allowlist.json` using `environment/export_student_view.py`.
It MUST NOT contain `sealed/`, evaluator exercises, answers, private tests, provenance review
material, or validation evidence. Handing the full production pack to a learner is a release error.

## 1. Filesystem paths

`safe_member_path(name: str) -> pathlib.PurePosixPath` MUST return a normalized, non-empty relative
POSIX path. It MUST reject absolute paths, `..` components, NUL bytes, backslashes, and non-string
input by raising `PathEscape`.

`resolve_beneath(root: Path, relative: PurePosixPath) -> Path` MUST return a path beneath `root` and
MUST reject escapes through existing symbolic-link parents. Comparing string prefixes is not enough.

## 2. Layer application

`LayerApplier.apply(archive_path: Path, destination: Path) -> None` imports an uncompressed or
standard-library-supported compressed tar layer. It MUST:

- preflight the entire archive before changing `destination`;
- enforce `LayerLimits` member, per-file, and total-byte limits;
- accept only directories and regular files;
- reject duplicate normalized member paths, links, devices, FIFOs, sockets, sparse surprises, and
  unsafe paths with `InvalidLayer` or `PathEscape`;
- stream file data without calling `extract()` or `extractall()`;
- normalize modes to `0755` for directories, `0755` for executable files, and `0644` otherwise;
- implement OCI-style `.wh.NAME` deletion and `.wh..wh..opq` opaque-directory markers without
  materializing the marker files; and
- never follow or create a symbolic link.

Whiteouts are processed before ordinary entries in the same layer. Failure during preflight MUST
leave the destination unchanged. Preflight includes the complete supplied destination ancestry and
all deterministic existing-tree type conflicts; it MUST reject a symlink in any existing destination
component without first resolving through that link.

## 3. Images

`ImageStore.import_image(name: str, layers: Sequence[Path]) -> ImageRecord` MUST validate a tag with
the regular expression `[a-z0-9][a-z0-9_.-]{0,63}`, require at least one layer, stage and hash each
layer in one byte-stream pass, and apply only those staged bytes. It derives a content digest from
the ordered SHA-256 layer digests. It MUST build in a private temporary directory and publish by
atomic rename. Same-content publication MUST be serialized across processes, while SQLite atomically
chooses the winner of competing tag claims. A losing claim MUST remove its newly published,
unreferenced object. A failed import MUST leave no object published by that attempt and no temporary
build directory.

Published image trees are immutable inputs: their modes MUST have no write bits, a canonical manifest
MUST bind the materialized tree digest, and integrity MUST be rechecked before a container copy.
Importing identical content under another unused tag MAY reuse the same snapshot. Rebinding an
existing tag to different content MUST raise `Conflict` without leaving the losing content object.

## 4. Durable state

`StateStore(root: Path)` owns `state.sqlite3` and records images and containers. Container IDs MUST be
monotonic per store (`c000001`, `c000002`, ...). Required states are `CREATED`, `RUNNING`, and
`EXITED`; the only legal transitions are `CREATED -> RUNNING -> EXITED`. A database trigger MUST
reject every other state change.

`claim_start(container_id)` MUST use an explicit `BEGIN IMMEDIATE` transaction so exactly one racing
caller claims a `CREATED` container. SQL MUST be parameterized. JSON fields MUST be canonicalized,
validated on read, and returned as typed records. `finish` records an integer exit code plus strings
for stdout and stderr.

## 5. Process runner

`ProcessRunner(max_output_bytes=65536, scratch_dir=None)` accepts an optional existing real directory
for capture scratch. Without one, capture files are placed in the validated `cwd`; that directory
therefore needs temporary-file permission. `run(argv, cwd, env, timeout) -> ExecutionResult` MUST
reject an empty argv, non-string arguments, invalid environment names, NUL bytes, non-positive
timeouts, and a non-directory `cwd`. It MUST use `subprocess.Popen` with `shell=False`, a new
session/process group, a small explicit base environment, and file-backed stdout/stderr capture.

On timeout, kill the entire process group and return exit code `124` with `timed_out=True`. The UTF-8
encoding of each returned stdout/stderr string, including marker overhead, MUST be no longer than
`max_output_bytes`. When data is discarded, reserve space for `\n...[truncated]\n` at limits of at
least 16 bytes, `[trunc]` at 7–15 bytes, `[...]` at 5–6 bytes, and `!` at 1–4 bytes; a zero-byte
limit has no room for a marker. Decode retained data with UTF-8 replacement without exceeding the
same bound.

## 6. Engine

`Docklet(root: Path)` coordinates the stores and runner:

- `import_image(name, layers)` imports and registers an image.
- `create(image_name, command, env=None)` verifies the published tree, makes a private writable
  regular-file copy of it, and returns a `ContainerRecord` in `CREATED` state.
- `start(container_id, timeout=5.0)` atomically claims, runs, and finishes a container. Internal launch
  failures MUST still leave the claimed record in `EXITED` with exit code `125`.
- `inspect(container_id)` returns the current typed record.

The child working directory is its rootfs and receives `PYDOCKLET_ROOT` pointing there. This variable
is a convenience, not confinement. Starting an `EXITED` or already `RUNNING` container raises
`InvalidTransition`.

## 7. CLI

`python -m pydocklet --root ROOT` MUST support `import`, `create`, `start`, `inspect`, and `list`.
Commands emit one canonical JSON object (or a JSON array for `list`) to stdout. Domain errors print a
single-line message to stderr and exit `2`; a completed container command returns the container's
exit code, except values outside `0..125` are mapped to `125`.

## Explicit non-goals

The baseline is not a real sandbox. Kernel namespaces, UID mappings, pivot-root, cgroups, seccomp,
network policy, registry protocols, copy-on-write mounts, interactive terminals, signals, and image
signing are outside scope. Document how those omissions affect trust.
