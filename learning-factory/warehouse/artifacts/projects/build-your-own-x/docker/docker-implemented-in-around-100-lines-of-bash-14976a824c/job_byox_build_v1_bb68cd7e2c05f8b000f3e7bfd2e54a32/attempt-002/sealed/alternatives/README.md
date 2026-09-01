# Alternative designs

These alternatives solve different versions of the problem. None is merely a
drop-in hardening flag for the teaching implementation.

## Delegate to an OCI runtime

Generate an OCI bundle and call a mature runtime such as `runc` or `crun` with
an argv array. This preserves a small educational control plane while
delegating namespace, capability, cgroup, seccomp, and lifecycle details. It
adds an external binary, a substantial configuration schema, version
compatibility work, and the need to validate bundles. This is the strongest
starting point among these options for real container semantics.

## Rootless user-namespace runtime

Use user namespaces with subordinate UID/GID mappings and a dedicated helper
that establishes mounts before executing a workload. This reduces host-root
exposure and can work for unprivileged learners. Host policy often disables or
restricts user namespaces, mapping helpers need careful installation, and some
filesystems and networking features remain unavailable.

## Bubblewrap-style sandbox adapter

Replace the default isolator with a fixed sandbox tool and translate the
runtime's narrow rootfs/command contract to its argv. This offers a concise,
well-tested isolation layer for desktop-style workloads. It is not a full
container lifecycle or image system, and availability varies by distribution.

## Persistent supervisor

Move lifecycle ownership into a small daemon written in a systems language.
Keep open pidfds, store transitions transactionally, authenticate clients, and
make cleanup independent of the invoking CLI process. This handles concurrent
operations and crash recovery better, but introduces a service trust boundary,
protocol, installation, upgrades, and operational monitoring.

## Process-only namespace laboratory

Drop rootfs switching and demonstrate only PID, UTS, IPC, and network namespace
effects around a host executable. This is safer to explain and needs fewer
filesystem privileges, but it no longer models a container filesystem. It can
be a useful earlier lesson before introducing mount namespaces and chroot.

## Proot or syscall emulation

An emulation layer can present an alternate root without privileged mounts and
works in constrained environments. Semantics and performance differ from
kernel-backed containment, and it should not be described as a security
boundary. It is useful as an availability fallback, not as evidence that the
namespace implementation works.

## Transactional state backend

Keep isolation unchanged but replace directory metadata with SQLite and an
explicit transition table. `BEGIN IMMEDIATE` transactions can claim names and
serialize lifecycle changes deterministically. Process liveness and signal
ownership still require OS evidence, and the database must not be held locked
while a workload runs. This option scales the control plane more cleanly than
adding ad hoc state files.

