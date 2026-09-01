# Productionization assessment

Status: **not productionized**.

Before any use with untrusted workloads, a new implementation and threat-model review should cover:

- descriptor-pinned, race-resistant rootfs resolution and verified image provenance;
- `pivot_root` or an equivalent detached mount-tree design, read-only base layers, masked kernel
  paths, safe device policy, and controlled writable storage;
- capability bounding, securebits, `no_new_privs`, seccomp, and an enforced LSM profile;
- cgroup v2 ownership and limits for memory, CPU, PIDs, and I/O, plus conservative rlimits;
- a retained init with specified signal forwarding, orphan reaping, cancellation, and timeout
  behavior;
- closure of unintended file descriptors and explicit terminal/session semantics;
- network policy, veth lifecycle, address management, firewalling, and DNS configuration;
- atomic state, crash recovery, cleanup ownership, audit logs, and stable machine-readable errors;
- multi-kernel integration, fuzz, race, failure-injection, and conformance testing in isolated CI;
- a supported Go/toolchain dependency policy and review of the frozen `syscall` API usage.

The current host lacked Go, and its namespace policy was not exercised. No build, runtime,
performance, fuzzing, hardening, or transfer claim is made. Independent validation is mandatory.
