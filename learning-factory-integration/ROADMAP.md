# Roadmap

Implemented foundations include the durable SQLite state machine, atomic claims and lease recovery,
bounded worker dispatch, exception-safe scheduler drain, independent validation, framed artifact
checksums, fsynced same-filesystem publication, startup integrity quarantine, immutable source-snapshot
history with one active commit, both source adapters, deterministic vertical slices, and operator
reporting. These remain regression-tested responsibilities rather than finished areas that may drift.

Immediate blocker: restore authorized standalone Codex access and complete a fresh independent
student/examiner pass. The present `401 Unauthorized` result is honestly recorded as
`blocked_authentication`; deterministic artifacts do not substitute for that live vertical slice.

1. Restore Codex authentication, retry the blocked student job, then retry its dependent examiner and
   archive the externally validated trajectory.
2. Deepen one CSDIY course cohort and one Build-Your-Own-X challenge pack.
3. Add bubblewrap/container profiles with network-disabled examiner runs.
4. Add operator tooling for inspecting and safely collecting unreferenced prepared artifact trees.
5. Ramp tier-one storage, networking, OS, distributed-systems, and language projects.
6. Generate measured architecture alternatives, debugging/review corpora, and transfer tasks.
7. Add cross-course synthesis, open-source archaeology, and sampled meta-evaluation.
8. Extend the implemented exec-backend subreaper boundary with cgroups or parent-death signals so a
   worker `SIGKILL` cannot orphan independently sessioned Codex/validator processes.
