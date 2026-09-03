# Sealed tradeoff analysis

## External `unshare` versus direct syscalls

An argv plan is observable and easy to unit-test without kernel privileges. It also inherits
util-linux version differences and splits setup between an external supervisor and Python helper.
Direct `clone3`, uid/gid map writes, mount APIs, and `pidfd` supervision provide tighter ordering and
error reporting, but require architecture-aware bindings and much more carefully audited code.

## `Path.resolve` versus descriptor-relative lookup

`resolve` plus `relative_to` clearly teaches sibling-prefix and existing-symlink failures. It is not
race-free. The reference intentionally states this limit rather than hiding it; `openat2` or pinned
directory descriptors are the production direction.

## JSON over stdin

Canonical JSON makes tests and evidence readable, avoids shell quoting, and keeps workload values out
of argv. It does not make environment values secret: process memory and downstream logs can still
expose them. The 1 MiB limit prevents unbounded setup input, while captured output remains another
known bound that production must add.

## Child-side proc mount

The reference mounts procfs from the already-namespaced helper because this build host returned
`EINVAL` for util-linux's path-valued `--mount-proc` form even though a direct proc mount succeeded.
This makes the ordering explicit and portable across that observed difference, at the cost of one
more privileged syscall in the Python helper.

## SQLite lifecycle state

SQLite gives local atomic claims, schema checks, and durable failed records with little machinery.
It is a poor fit for a distributed daemon without one ownership boundary, and the reference does not
attempt crash reconciliation between `RUNNING` database state and real processes. A production
runtime would store pidfds or start identity, reconcile on startup, and protect the database itself
from untrusted writers.

## Safety defaults

Read-only root and an empty network namespace are defaults because accidental sharing is more
dangerous than an early failure. A setup-only preflight now turns unsupported mount behavior into an
error before workload exec, while leaving a small preflight/launch race. It never silently retries
writable. The `network: true` model is intentionally crude. No configuration option can compensate
for missing cgroups, seccomp, capability dropping, and verified rootfs input.

## One complete source versus two distribution views

Keeping reference and learner stages in one production pack preserves reviewability, but that tree
cannot honestly be called learner-sealed. A deterministic allowlist exporter produces separate
learner and instructor directories. Content manifests add auditable completeness and integrity at
the cost of requiring the distributor to retain the printed manifest digest outside each view.
