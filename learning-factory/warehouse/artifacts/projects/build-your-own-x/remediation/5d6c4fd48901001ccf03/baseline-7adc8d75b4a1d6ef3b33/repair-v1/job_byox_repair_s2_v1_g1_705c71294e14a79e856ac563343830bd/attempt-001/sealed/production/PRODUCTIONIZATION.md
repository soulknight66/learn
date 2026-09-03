# Productionization assessment

Production status: **not productionized**. The following work is required before any reconsideration:

- define a hostile-workload threat model and supported kernel/util-linux matrix;
- replace path validation/setup with descriptor-pinned Linux APIs and a verified, traversal-safe
  rootfs extraction pipeline;
- run a minimal audited native init/setup helper, drop bounding/ambient capabilities, set
  `no_new_privs`, and install seccomp plus an LSM profile;
- create cgroup v2 limits before workload release, supervise through pidfds, and use cgroup-wide kill;
- configure loopback/veth/routes/firewall explicitly or keep an empty network namespace;
- stream logs to bounded files with ownership, redaction, rotation, and durable provenance;
- make start/finish and crash recovery reconcile database identity with non-reusable process identity;
- protect SQLite permissions and migration ownership, make evidence fields append-only, and test power
  loss and disk-full behavior;
- add kernel integration tests for mount propagation, proc PID views, UID mapping, signal forwarding,
  zombie reaping, timeouts, fork bombs, file descriptor inheritance, and cleanup;
- fuzz spec parsing and filesystem extraction, measure resource behavior with declared methodology,
  and obtain an independent security review.

No production implementation is supplied because these controls cannot be honestly demonstrated in
this restricted build environment. The sealed reference remains intentionally educational.
