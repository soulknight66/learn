# Concepts

## A container is a constrained process

A container is not a tiny virtual machine. At runtime it is an ordinary host process observed through restricted kernel interfaces. A container tool prepares filesystem state and configuration, asks the kernel to create isolation boundaries, launches a process, and records what happened.

## Linux namespaces

Each namespace virtualizes one aspect of process-visible state. MiniBox asks for PID (process numbering), mount (mount table), UTS (hostname/domain), IPC, and user namespaces. A network namespace is optional because an empty network namespace changes connectivity and requires further setup. Namespace flags alone are not a security boundary: capabilities, seccomp, cgroups, and LSMs matter too.

User namespaces can map an unprivileged host user to UID 0 *inside* the namespace. Whether this is enabled is a host policy decision. PID namespace behavior also requires a child process: the caller remains outside, while the forked child becomes PID 1 in the new namespace.

## Root filesystems and layers

Changing the apparent root directory gives a process a filesystem view, but a useful rootfs must contain its executable and dynamic-loader dependencies. An image layer is often represented as a tar archive. Tar paths and link metadata are attacker-controlled input, so generic extraction helpers are unsafe for this exercise. Whiteouts represent deletion relative to a lower layer; opaque markers hide all lower children of a directory.

## Control plane versus runtime

Filesystem preparation and durable lifecycle records form a control plane. The isolated payload is the data plane. Keeping them separate makes tests deterministic: state transitions and argv plans can be validated on hosts that disallow real namespace creation.

## Compare-and-transition

Two callers can observe the same current state and both try to run a container. A write transaction plus an expected-state predicate ensures only one wins. A database trigger provides a second line of defense so a programming mistake cannot create a forbidden edge.

## Process groups and timeouts

Killing only a direct child may leave grandchildren running. Starting a new session creates a process group that can be terminated as a unit. Output capture also needs a bound: an isolated process can still exhaust memory by writing forever.
