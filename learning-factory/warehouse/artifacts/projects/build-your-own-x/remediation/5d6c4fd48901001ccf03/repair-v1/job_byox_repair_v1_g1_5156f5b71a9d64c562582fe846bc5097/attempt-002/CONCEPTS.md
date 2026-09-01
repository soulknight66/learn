# Concepts behind Minibox

This chapter supplies vocabulary and mental models, not an implementation
recipe. The design questions remain yours to answer.

## A container is a constrained process

A Linux container is not a small virtual machine. It is one or more ordinary
host-kernel processes whose view of selected resources has been changed and
whose permissions and resource use have been constrained. Namespace membership
can change what a process sees, but visibility and authority are different
questions. A process may have a private hostname view while retaining access to
dangerous files, devices, system calls, or host resources.

That distinction is why Minibox calls its deterministic object an
`IsolationPlan`. Constructing an argument vector says what should be requested;
only successful kernel operations and correct child setup can establish it.

## Namespace roles

Minibox discusses six Linux namespace types:

- A **user namespace** gives user and group IDs a namespace-specific mapping.
  “Root” inside such a mapping is not automatically host root.
- A **mount namespace** gives processes a separate mount-table view. Creating
  one does not by itself replace the root directory or make existing mounts
  private.
- A **PID namespace** changes process-ID visibility. The first child has
  special lifecycle and signal-handling responsibilities.
- A **UTS namespace** separates hostname and domain-name state.
- An **IPC namespace** separates several System V and POSIX IPC resources.
- A **network namespace** separates interfaces, routes, ports, and related
  network state. A fresh namespace also needs deliberate network setup to be
  useful.

User namespaces are governed by kernel features *and* local policy. A sysctl
that appears permissive, an `unshare` executable on PATH, or namespace entries
under `/proc` is only partial evidence. Outer containers, LSM policy, seccomp,
distribution patches, and CI restrictions can still reject the operation.

## A rootfs path is not a root filesystem boundary

A directory tree can model the files a guest should see. Joining a configured
directory with a command name, however, does not change the process's root and
does not confine later filesystem access. Path validation and runtime
filesystem isolation solve related but different problems.

Three path forms deserve separate thought:

- **Host paths** are interpreted by the Python process's current filesystem
  view.
- **Guest absolute paths** begin with `/` but are intended to be rooted in the
  configured guest tree.
- **PATH entries** are a search policy and may themselves contain malformed or
  adversarial locations.

Lexical normalization handles text such as `.` and `..`; filesystem resolution
also encounters symbolic links and races. A containment check performed before
opening a file can become stale if another actor can replace path components.
Minibox adopts deliberately conservative symlink rules, but this exercise still
does not claim to eliminate every time-of-check/time-of-use race on a hostile,
concurrently modified filesystem.

Executable permission is also contextual. Mode bits, mount flags, ACLs,
interpreters, architecture, and current credentials can all affect whether the
kernel can execute a file. The deterministic resolver checks the narrower
contract stated in the requirements.

## Closed schemas create a trust boundary

Configuration validation is more than checking that three keys are present. A
closed schema rejects misspellings and unknown future behavior instead of
silently guessing. It separates JSON representation types from Python's
surprising type relationships—for example, booleans are integers in Python—and
it prevents later mutation of caller-owned containers from changing a
validated value behind the runtime's back.

Defaults are policy. A default PATH decides which guest directories are
searched; a default network mode decides whether network isolation is
requested; a timeout bounds how long execution can occupy resources. They
should therefore be explicit and testable.

## State machines make lifecycle rules visible

A lifecycle status is useful only when its allowed transitions are defined.
Without a state machine, two workers might both decide that an object is ready
to run, or an old writer might overwrite a newer result.

Minibox combines three ideas:

- **Expected-state comparison** asks the caller to name the state it believes
  it is replacing.
- **A transition table** limits which status edges are legal.
- **A revision** provides a monotonic record of successful changes.

Atomic publication prevents readers from observing half a JSON document. It is
not identical to concurrency control: publishing two individually complete
documents can still lose an update unless comparison and publication are part
of one protected operation. Likewise, atomic publication is not automatically
equivalent to power-loss durability or coordination across machines.

There is also a commit-point distinction. Once an atomic rename or link makes a
complete record visible, a later directory-sync error cannot truthfully mean
“nothing happened.” The caller needs a distinct uncertain outcome, the exact
intended record, and a reconciliation operation that reads before it retries
durability. Repeating the original mutation blindly can turn a real success
into a misleading duplicate or stale-state error.

An injectable clock keeps timestamps meaningful in production code and
predictable in tests. Preserving terminal records is important evidence: an
error should not erase the fact that an attempt reached `RUNNING` and failed.

## Dependency inversion keeps tests honest

Namespace support is environmental and subprocess behavior is slow and
failure-prone. If lifecycle code directly calls `unshare`, ordinary unit tests
become tests of the host machine. A small backend boundary lets the runtime
exercise success, nonzero exit, and setup failure deterministically while a
Linux implementation handles process mechanics separately.

This separation also clarifies two different outcomes:

- A payload can run successfully from the backend's perspective and return a
  nonzero exit code.
- A backend can fail to start or supervise the payload at all.

Conflating them loses information and makes retry policy unsafe.

## Process supervision is part of correctness

Shell command strings combine data and syntax, so an argument controlled by a
configuration can unexpectedly become an operator, expansion, or redirection.
Argument-vector APIs preserve the data boundary.

Timeouts must cover the process tree, not just a convenient parent. Captured
stdout and stderr are byte streams; decoding is an application policy and may
fail for arbitrary payload output. Signals, PID-namespace init behavior, pipe
capacity, and cleanup after partial setup all matter in a real backend.

## The missing production layers

A production container runtime must address far more than this exercise:
verified image extraction, mount propagation, read-only and masked paths,
capability bounding, `no_new_privs`, seccomp, cgroups, device policy, secrets,
network configuration, signal forwarding, zombie reaping, logging limits,
concurrent lifecycle operations, recovery after crashes, and careful use of
race-resistant filesystem APIs.

Minibox exposes several of those fault lines for study. It intentionally does
not certify a security boundary or implement the OCI specifications.
