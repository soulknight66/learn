# Productionization assessment

Status: **not productionized**. This file is a gap analysis, not a certification
or a production implementation.

Before deployment, a substantially different kernel would need at least:

- verified exception vectors, abort recovery, syscall ABI, and unprivileged tasks;
- interrupt-driven preemption with nested-interrupt and critical-section rules;
- hardware-enforced per-process page tables, W^X, guard pages, and TLB discipline;
- race-safe lifecycle, filesystem, driver, and allocator synchronization;
- capability or credential checks at every resource boundary;
- resource quotas, cancellation, watchdog recovery, and denial-of-service limits;
- persistent storage semantics, integrity, crash recovery, and wear/error handling;
- physical-board bring-up, cache/coherency handling, DMA/IOMMU policy, and SMP;
- reproducible signed builds, SBOM and license review, secure boot, update/rollback,
  vulnerability response, and operational telemetry;
- fuzzing of parsers and syscalls, fault injection, long-duration stress, formal
  invariant work, and independent security review.

The present QEMU boot, host sanitizers, and deterministic unit checks establish
none of those production properties. No performance, reliability, security, or
hardware-portability claim is made.
