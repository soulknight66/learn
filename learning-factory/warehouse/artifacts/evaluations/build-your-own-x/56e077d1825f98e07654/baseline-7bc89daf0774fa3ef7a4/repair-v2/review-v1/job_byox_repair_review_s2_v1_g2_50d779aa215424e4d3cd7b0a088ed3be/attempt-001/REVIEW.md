# Independent review

Verdict: **REVISE**. The reference kernel has a reproducible high-severity task-identity defect. It must not receive an advisory PASS or a `REVIEWED` label in this state.

Controller evidence binding: `controller-audit-sha256:9768c1e824f3afcf1d3668dbf93c7ce0c7ee31a1783e44fc0e7ee791b2461985`.

## Prioritized findings

### P0 / High — a stale physical return kills a replacement in a reused slot

The controller finding is confirmed independently and byte-for-byte. The audited candidate sources have the expected hashes:

- `sealed/reference/kernel/runtime.c`: `4bcb6d4619a949e0a395168434db180bc1cc7d41b490cdb65a03c6f62527e919`
- `sealed/reference/kernel/scheduler.c`: `8ba0e4915ed997dacb161212a7b423e927a01126b027621c927b0f0e802aab9c`

An independently authored ARM probe ran this legal sequence from the only active task: exit the logical task, reap its PID, spawn a replacement into the freed slot, select that replacement through the scheduler, and return from the still-executing outer frame. QEMU then emitted:

```text
REENTRANT-PROBE
OUTER-RETURN
BUG-STALE-RETURN-KILLED-REPLACEMENT
```

`REPLACEMENT-RAN` and `NO-BUG` were absent. The 68 raw UART bytes had SHA-256 `08865798fa3b5544fdfc927e022f64c1d430e9d252feef2077185526f03ae7e7`; after CRLF normalization, the 65 bytes had SHA-256 `ab9b3fe67c8febba717d224c9c56d79529131bd50ab01051f5babca838bef62a`. Both values exactly match the controller observation.

The implementation tracks logical selection but not the identity of the physical frame that is still executing:

- `runtime.c:19-25` obtains bootstrap entry data from mutable `scheduler.current_slot` and later calls a global `lf_runtime_exit()` with no captured PID/generation.
- `runtime.c:101-109` and `runtime.c:123-132` choose context ownership solely from the scheduler's current slot.
- `scheduler.c:91-145` permits the old PID to become a zombie, be reaped, and have its slot reused while the old ARM frame can still execute.
- `runtime.c:61-68` initializes the replacement context in that same slot without proving that no stale physical owner remains.

Consequently, the stale return treats the newly selected replacement as the exiting task, marks it zombie, and overwrites its context without ever running its entry point. This can silently discard runnable work and corrupt suspended state. It contradicts the task-return contract and invalidates the sealed design's claim that the policy/runtime split preserves task identity.

Required remediation:

1. Bind active execution to a physical task identity that includes PID and slot identity/generation, not slot alone.
2. Reject or safely resolve stale yield/exit operations; a stale frame must not mutate a reused slot or save into its context.
3. Honor a runnable task already selected by reentrant scheduler activity.
4. Add a harness-controlled ARM/QEMU regression requiring `REENTRANT-PROBE`, `REPLACEMENT-RAN`, and `NO-BUG`, while forbidding `OUTER-RETURN` and `BUG-STALE-RETURN-KILLED-REPLACEMENT` as appropriate for the repaired flow.
5. Update the sealed rationale and learner design review to explain physical execution identity across reap/reuse.

### P1 / Medium — green suites do not cover the runtime/context ownership boundary

The nominal evidence is real but insufficient. The reference suite passed 407 checks and the adversarial runner passed 12 vectors. However, both Makefiles compile only `scheduler.c`, `vm.c`, and `ramfs.c`; neither compiles `runtime.c` nor `arch/arm/context.S`. The adversarial `pid_stale_reuse` vector confirms logical slot reuse but never leaves a stale physical stack frame executing. The QEMU demo exercises ordinary `ABABAB` yields and task returns without reap/reuse reentrancy.

The passing counts therefore cannot detect P0. The repair needs architecture-level regression coverage in addition to the existing host state-machine tests. Candidate-authored scripts or UART success text alone are not acceptance evidence.

## Other review dimensions

- **Reproducibility:** Good apart from the correctness failure. A clean build in a writable review copy was byte-identical to the submitted ELF and binary. The nominal ELF booted and printed the documented markers. Its entry point, segment permissions, and lack of unresolved symbols were independently confirmed.
- **Progressive disclosure:** Independently materialized initial and post-attempt views passed strict inventory audits. Both included `LICENSE_BOUNDARY.md`; neither exposed a forbidden `sealed`, `reference`, answer, solution, or hidden-test component.
- **License/provenance:** The documents clearly distinguish the CC0 catalog metadata from the linked repository's `NOASSERTION` license and place generated content under an explicit all-rights-reserved boundary. Internal identifiers and hashes are consistent. Independent authorship and upstream licensing remain unverified because no upstream snapshot or network comparison was available.
- **Learner usefulness:** Requirements, staged feedback, design questions, and failure-atomicity guidance are generally clear. P0 is blocking because the reference implementation and sealed explanation teach an incomplete identity model and can reject a correct learner diagnosis or bless a broken runtime.
- **Validation honesty:** The manifest stays `GENERATED`/`PARTIAL`, requires independent validation, and keeps `productionized` false. The candidate explicitly disclaims `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, and `PRODUCTIONIZED` promotion. No dishonest label promotion was found.

Only a separate orchestrator-captured acceptance validator may publish `REVIEWED` after the runtime repair and regression pass.
