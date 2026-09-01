# Behavioral requirements

Implement the exported API already declared in `starter/api.go`. Do not change its signatures.

## Configuration and parsing

- **R1** `DefaultConfig` supplies hostname `tinybox`, `/proc` mounting, user-namespace use, and a
  small deterministic environment.
- **R2** `ValidateConfig` accepts only an absolute, already-clean rootfs directory. The directory
  itself must not be a symbolic link, and `/` must be rejected.
- **R3** When `/proc` mounting is enabled, `<rootfs>/proc` must be an existing real directory.
- **R4** A hostname is 1–63 ASCII bytes, consists of dot-separated alphanumeric/hyphen labels, and
  has no empty label or leading/trailing hyphen.
- **R5** The requested command is nonempty. Its executable path is absolute and clean. Arguments
  contain no NUL bytes.
- **R6** Environment entries have the form `NAME=value`; names match shell-portable identifier
  syntax, names are unique, and entries contain no NUL byte.
- **R7** `ParseRunArgs` accepts `run`, `--rootfs`, `--hostname`, `--mount-proc`, `--userns`, repeated
  `--env`, and a command after `--`. It applies defaults and validates the result.
- **R8** `EncodeChildArgs` and `ParseChildArgs` round-trip every configuration field without shell
  parsing. Only the exact internal marker is a child invocation.

## Deterministic launch planning

- **R9** A launch plan uses an absolute, clean current-executable path and records argv separately
  from that path.
- **R10** Every launch uses fresh UTS, PID, mount, IPC, and network namespaces.
- **R11** If requested, a fresh user namespace maps container ID 0 to exactly the supplied host UID
  and GID, with setgroups disabled. Negative IDs are invalid.
- **R12** Planning performs no namespace, mount, chroot, or exec side effect.

## Runtime behavior (Linux only)

- **R13** `Run` re-executes the current binary using the plan, connects the supplied standard I/O,
  applies a parent-death signal, and honors context cancellation.
- **R14** Runtime setup failures are contextual errors. A normal contained-process exit becomes an
  `ExitError` with the same exit status; signal exits use the conventional `128 + signal` status.
- **R15** The internal child validates again, makes `/` recursively private, bind-mounts the rootfs
  onto itself, sets the hostname, changes root and working directory, and optionally mounts a fresh
  proc filesystem.
- **R16** After successful setup, the bootstrap process is replaced by the requested executable. A
  setup failure must never fall through and run the command on the host root filesystem.
- **R17** Non-Linux builds return `ErrNotLinux` for namespace/runtime operations while pure parsing
  and validation remain usable.

## Safety and quality

- **R18** Use only standard-library packages. Never construct a shell command string.
- **R19** Unit tests must not enter namespaces or modify mounts. Integration execution is opt-in via
  `TINYCONTAINER_INTEGRATION_ROOTFS` and is intended only for disposable Linux VMs.
- **R20** Error messages must identify the failed phase without embedding environment values.

## Explicit non-goals

This exercise does not implement cgroups, OCI images/specifications, overlay filesystems, seccomp,
LSMs, capability bounding, idmapped mounts, networking setup, daemon lifecycle, checkpointing, or
production-grade rootfs race prevention. Completion is educational, not production readiness.
