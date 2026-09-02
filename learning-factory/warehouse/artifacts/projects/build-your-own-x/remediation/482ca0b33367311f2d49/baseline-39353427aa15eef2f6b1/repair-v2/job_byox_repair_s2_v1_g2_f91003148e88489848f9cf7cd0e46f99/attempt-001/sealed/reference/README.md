# Sealed reference implementation

This directory contains the evaluator-only implementation of the public `pydocklet` contract. It is
independently generated for this challenge and uses only Python's standard library.

It targets POSIX because image publication uses per-content `fcntl.flock` locks around filesystem
publication and cleanup. Layer bytes are staged while hashing; published trees are made read-only and
verified against their canonical manifest before container copying.

It models layers, snapshots, state claims, and bounded process execution. It does not claim kernel
confinement. Run it only through the validation commands in the repository-level `VALIDATION.md`.
