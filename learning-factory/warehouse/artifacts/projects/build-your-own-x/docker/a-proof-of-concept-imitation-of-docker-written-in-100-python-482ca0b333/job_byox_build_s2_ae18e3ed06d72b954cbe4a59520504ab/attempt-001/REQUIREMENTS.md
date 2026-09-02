# Requirements

Implement a Python 3.11 package named `pydocklet`. Only the standard library may be used. The terms
MUST, SHOULD, and MAY describe the learner contract.

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
leave the destination unchanged.

## 3. Images

`ImageStore.import_image(name: str, layers: Sequence[Path]) -> ImageRecord` MUST validate a tag with
the regular expression `[a-z0-9][a-z0-9_.-]{0,63}`, require at least one layer, hash the exact bytes
of each layer with SHA-256, and derive a content digest from the ordered layer digests. It MUST build
in a private temporary directory and publish by atomic rename. A failed import MUST leave no
published image and no temporary build directory.

Published image trees are immutable inputs. Importing identical content under another unused tag MAY
reuse the same snapshot. Rebinding an existing tag to different content MUST raise `Conflict`.

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

`ProcessRunner.run(argv, cwd, env, timeout) -> ExecutionResult` MUST reject an empty argv, non-string
arguments, invalid environment names, NUL bytes, non-positive timeouts, and a non-directory `cwd`.
It MUST use `subprocess.Popen` with `shell=False`, a new session/process group, a small explicit base
environment, and file-backed stdout/stderr capture.

On timeout, kill the entire process group and return exit code `124` with `timed_out=True`. Captured
stdout and stderr MUST each be bounded to `max_output_bytes`; add a visible truncation marker when
data is discarded. Decode with UTF-8 replacement.

## 6. Engine

`Docklet(root: Path)` coordinates the stores and runner:

- `import_image(name, layers)` imports and registers an image.
- `create(image_name, command, env=None)` makes a private regular-file copy of an image rootfs and
  returns a `ContainerRecord` in `CREATED` state.
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
