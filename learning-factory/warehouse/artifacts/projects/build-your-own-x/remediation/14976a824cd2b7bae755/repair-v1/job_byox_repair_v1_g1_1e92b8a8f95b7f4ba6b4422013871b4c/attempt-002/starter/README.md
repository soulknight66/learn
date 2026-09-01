# Starter guide

Edit `minictr`, `lib/runtime.sh`, and `lib/isolate.sh` to complete the exercise. The entry point already
handles command dispatch, argument counts, basic name/rootfs validation, and `MINICTR_HOME` defaults.
It intentionally does not create state or namespaces.

## Files and boundaries

- `minictr` is the CLI boundary. Keep parsing and user-facing diagnostics here.
- `lib/runtime.sh` owns durable registrations, transient run state, locking, cleanup, and `ps` output.
- `lib/isolate.sh` owns Linux namespaces, mount/root setup, and execution inside the selected rootfs.

The entry point sources `lib/runtime.sh` because it is trusted static code shipped with the project.
Never extend that pattern to runtime metadata. Registration files are data and must be read with data
operations.

## Required runtime function interfaces

The entry point calls these functions:

```text
minictr_runtime_create NAME ROOTFS
minictr_runtime_run NAME COMMAND [ARG...]
minictr_runtime_ps
minictr_runtime_delete NAME
```

Return status and output are observable CLI behavior, so do not hide a child failure behind unconditional
success. Preserve the array already created for command arguments.

The name grammar is ASCII, not a locale collation rule. Keep validation
bytewise (for example, in a local C locale) so a registration created under one
locale cannot become invisible or undeletable under another.

## The isolator seam

When `MINICTR_ISOLATOR` is nonempty, the runtime must invoke that single executable path as:

```text
ISOLATOR ROOTFS COMMAND [ARG...]
```

Do not interpret it as a string containing a command and flags. Do not use `eval` or a second shell.
Resolve a relative path from the caller's current working directory rather than searching `PATH`.
When it is unset, resolve `lib/isolate.sh` relative to the MiniCTR program directory so the CLI works
from any current working directory.

The public fake understands additional `MINICTR_FAKE_*` variables. Those belong to the fake test helper,
not to your runtime API; simply allow ordinary environment inheritance when invoking the helper.

## Recommended milestones

### 1. Durable idle registrations

Implement `create`, empty/nonempty `ps`, duplicate detection, and `delete`. Check the exact TSV contract.
Resolve the prospective state root before writing it and reject either-direction overlap with the
canonical rootfs, including when `MINICTR_HOME` does not exist yet.
Use a fresh temporary `MINICTR_HOME` while experimenting:

```bash
work=$(mktemp -d)
rootfs=$(mktemp -d)
MINICTR_HOME=$work/state ./starter/minictr create demo "$rootfs"
MINICTR_HOME=$work/state ./starter/minictr ps
```

Remove those disposable directories yourself after inspecting them. MiniCTR must never delete the
registered rootfs.

### 2. Fake-isolator execution

Implement lookup and invocation without namespace code. The public fake checks argument boundaries,
standard streams, and nonzero status propagation. Pay particular attention to empty arguments and text
that would be meaningful only if passed through a shell parser.

### 3. Lifecycle exclusion

Add an atomic active-run claim shared by `run`, `ps`, and `delete`. The fake can pause so another process
observes the active state. Define stale-state recovery before coding it.

### 4. Linux isolation

Only after the rootless suite passes, replace the TODO in `lib/isolate.sh`. Read `CONCEPTS.md`, determine
what your host permits, and fail closed when the full required setup cannot be established.

## Testing

From the repository root:

```bash
bash -n starter/minictr starter/lib/runtime.sh starter/lib/isolate.sh
bash public_tests/test_minictr.sh
```

The untouched starter should report TODO diagnostics and failing functional cases. A learner solution
should make the suite pass without editing anything under `public_tests/`.

## Before declaring completion

- Search your code for `eval`, dynamic `source`, `bash -c`, and unquoted caller-derived expansions.
- Test from a working directory outside the repository.
- Test names and rootfs paths containing allowed punctuation and spaces.
- Verify a child exit greater than 1 survives the wrapper.
- Verify cleanup after an interrupted, failing, and successful run.
- Verify `delete` never follows a stored path into the rootfs.
- Keep fake-isolator evidence separate from real namespace evidence.
