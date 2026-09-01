# Alternative designs

These are independent extensions or replacements for the reference architecture.

## Descriptor-pinned rootfs launcher

Open the rootfs once, traverse the command relative to that descriptor, and reject escapes using
kernel-enforced resolution flags. Pass only already-open descriptors to a small native launcher,
which constructs a private mount tree and executes by descriptor. This substantially improves path
integrity but requires Linux-specific syscall handling and careful executable/interpreter semantics.

## Rootless OCI-style launcher

Translate the small Minibox specification into an OCI runtime specification and delegate low-level
setup to an established runtime. This gains mature namespace, mount, capability, seccomp, and cgroup
handling. It hides much of the mechanism the exercise is intended to teach and introduces a large
external dependency and compatibility surface.

## Supervisor daemon with SQLite state

Move ownership into one long-lived supervisor. Persist desired and observed state, leases, pidfds,
and audit events transactionally in SQLite. Clients submit requests over an authenticated local
socket. This gives clearer crash recovery and concurrency, but demands authentication, protocol
versioning, daemon lifecycle management, and migration discipline.

## Per-container virtual machine

Execute the rootfs under a microVM rather than sharing the host kernel. The boundary is stronger for
hostile code, at a cost in startup latency, memory, image construction, device emulation, and
operational complexity. A VM still needs resource accounting and a hardened control plane.

## Simulation-only teaching backend

Retain the strict spec, resolver fixtures, namespace plans, and state machine, but never invoke
privileged Linux operations. A simulator can make the workshop portable and deterministic. It must
be labeled as a model: it cannot demonstrate that a kernel actually isolates processes.

