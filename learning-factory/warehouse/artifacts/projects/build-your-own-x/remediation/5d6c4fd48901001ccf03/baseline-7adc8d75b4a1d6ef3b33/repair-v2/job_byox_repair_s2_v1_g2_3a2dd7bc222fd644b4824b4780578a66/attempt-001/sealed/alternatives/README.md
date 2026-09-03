# Sealed alternatives

## Direct syscall backend

A lower-level runtime could call `clone3` with namespace flags, write `/proc/<pid>/uid_map` and
`gid_map`, use the new mount API, and supervise through a pidfd. This removes dependency on the
util-linux CLI and gives precise ordering, but Python's standard library does not expose the full
surface. `ctypes` bindings would need architecture and kernel-version tests and careful structure
layouts; a small memory-safe native helper is generally easier to audit.

## Bubblewrap-style delegated backend

Delegating setup to a mature sandbox tool reduces custom kernel code, but changes the learning goal
and adds a dependency whose exact policy must be pinned and validated. It still does not provide
cgroups, image management, or lifecycle persistence by itself.

## OCI runtime adapter

Generating an OCI bundle and invoking an established runtime is the pragmatic interoperability
route. It is no longer “rebuild the core boundary,” and it introduces a larger specification,
runtime discovery, bundle ownership, and compatibility matrix.

## Descriptor-safe path backend

Replace `Path.resolve` with a Linux-specific `openat2` wrapper rooted at an `O_PATH` descriptor, then
adopt `open_tree`, `move_mount`, and `mount_setattr`. This directly addresses the reference's largest
filesystem race at the cost of leaving portable Python.
