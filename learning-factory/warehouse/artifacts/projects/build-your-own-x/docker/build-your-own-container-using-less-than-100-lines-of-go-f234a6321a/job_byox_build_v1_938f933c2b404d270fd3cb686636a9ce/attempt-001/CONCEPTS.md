# Concepts behind the challenge

## A container is a configured process

Linux containers are ordinary processes observed through selected kernel isolation mechanisms. The
runner in this project asks the kernel to create a child in several new namespaces and then changes
the filesystem view before executing the workload. There is no container object independent of
those processes.

## Namespace dimensions

- A **UTS namespace** gives the child a hostname distinct from the host.
- A **PID namespace** gives the first child PID 1 and hides host process IDs from its descendants.
- A **mount namespace** permits a different mount table. Making its root mount private prevents
  later mounts from propagating back through shared mount relationships.
- An **IPC namespace** separates System V IPC and POSIX message-queue resources.
- A **network namespace** starts with isolated interfaces and routing state; this exercise does not
  configure connectivity.
- A **user namespace** can map an unprivileged host identity to UID/GID 0 inside. That grants
  capabilities only in namespaces governed by that user namespace, subject to kernel policy.

Namespaces isolate views; they do not limit CPU, memory, I/O, or process counts. Cgroups normally
provide those controls.

## PID 1 and re-execution

Namespace flags apply when a process is created, so the parent launches another copy of its own
binary with an unambiguous internal marker. Inside a PID namespace, the first process has special
signal and orphan-reaping semantics. This exercise replaces the bootstrap image with the workload,
making the workload PID 1. A fuller runtime would normally retain a small init process to forward
signals and reap orphaned descendants.

## Filesystem view

`chroot` changes pathname resolution for a process but is not, by itself, a robust security boundary.
This project combines it with a private mount namespace and a self bind-mount. It still has time-of-
check/time-of-use races and lacks defenses such as `pivot_root`, `openat2` resolution constraints,
read-only mounts, masked paths, and capability removal.

The rootfs must already contain the executable and any dynamic loader or shared libraries it needs.
A statically linked probe avoids those runtime dependencies in the supplied integration fixture.

## Determinism before privilege

Configuration validation, argument encoding, and launch planning are ordinary pure-ish code and can
be tested without privileges. Separating them from mount and namespace syscalls gives fast,
repeatable feedback and sharply limits what a unit-test failure can disturb.
