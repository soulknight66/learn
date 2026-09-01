# Sealed alternative designs

Three reasonable continuations were considered but intentionally not implemented in the reference:

- **Retained init:** keep the Go child as PID 1, start the workload as PID 2, forward a documented
  signal set, reap with `wait4`, and return the workload status. This is the best next learning step.
- **Descriptor-pinned pivot:** open the rootfs with constrained resolution, create a detached mount
  tree, pivot to it, detach the old root, and close every host descriptor. This addresses several
  filesystem races but requires newer Linux APIs and substantially more test scaffolding.
- **OCI handoff:** generate an OCI bundle and invoke a reviewed OCI runtime. This transfers low-level
  implementation responsibility but changes the project from “build a runner” to “build a frontend”
  and introduces an external binary and spec-version dependency.

Other namespace creation APIs such as `clone3` can return pidfds and improve lifecycle control. They
would require raw syscall wrappers or an external syscall package, neither of which fits this
dependency-free starter.
