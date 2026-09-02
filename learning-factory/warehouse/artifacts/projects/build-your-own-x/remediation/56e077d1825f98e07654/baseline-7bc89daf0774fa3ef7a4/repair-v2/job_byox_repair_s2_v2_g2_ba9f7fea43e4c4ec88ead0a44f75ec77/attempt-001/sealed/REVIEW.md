# Sealed implementation review

## Review scope

The review covered integer boundaries, table state transitions, failure
atomicity, freestanding linkage, ARM ABI context layout, MMU enable ordering,
serial evidence, and learner/reference isolation.

## Resolved findings

- **High — task return continuation:** New stacks have no caller. The runtime now
  enters a non-returning bootstrap, and normal task return invokes the zombie
  transition rather than consuming arbitrary stack data.
- **High — physical identity across slot reuse:** The runtime binds active
  execution and saved contexts to both slot and PID. A stale frame cannot exit a
  replacement or overwrite its register image, and a replacement already
  selected by policy is dispatched without an extra rotation.
- **High — range overflow:** Frame-pool end uses 64-bit arithmetic. RAMFS checks
  `offset > UINT32_MAX - length` before addition. Translation checks permission
  before computing the final address.
- **Medium — partial filesystem mutation:** Create and write perform all failing
  checks before mutation. Unlink scrubs inline bytes before releasing a slot.
- **Medium — corrupted scheduler input:** Every mutation validates uniqueness and
  running/current agreement, and refuses a corrupt table without further change.
- **Medium — ELF memory permissions:** RX code/rodata and RW data/BSS/stack use
  distinct program headers; the GNU stack request is explicitly non-executable.
- **Low — runtime exit misuse:** Calling exit outside an active task now stops at
  a guarded non-returning path instead of dereferencing a null runtime.

## Accepted limitations

- Scheduling is cooperative; there is no timer IRQ, preemption lock, or fairness
  guarantee against a hostile task.
- All tasks execute in privileged mode and share the identity-mapped hardware
  address space. Software mapping permissions are validated logic, not a security
  boundary.
- There are no exception vectors, fault diagnostics, syscalls, user stacks,
  locks, atomic instructions, or multicore rules.
- RAMFS assumes single-threaded calls, has no directories or persistence, and
  authenticates neither callers nor names.
- UART polling has no timeout if a modeled device remains permanently full.
- Hardware evidence is QEMU `versatilepb`, not a physical ARM board.

## Review conclusion

The implementation is proportionate to the learning contract and its observed
tests. It must remain `productionized: false`, `GENERATED`, and `PARTIAL` until
independent validation; the limitations above also prevent any later validator
from treating this reference unchanged as a production kernel.

## Repair generation 1 follow-up

The archived independent review drove five bounded candidate changes:

- the adversarial file now contains 12 schema-checked vectors and a deterministic
  executor, including every boundary advertised by its README;
- publication inputs now have an explicit machine-readable allowlist and a
  strict view auditor, while actual materialization evidence remains an external
  orchestrator gate;
- initializers canonicalize padding and mutation tests snapshot raw bytes with
  `memcpy` instead of structure assignment;
- the path-dependent sealed host-test executable is omitted as scratch output;
- `LICENSE_BOUNDARY.md` now states an explicit all-rights-reserved policy for
  generated material rather than treating an intended use as a license grant.

These repairs are locally exercised in `VALIDATION.md`; they do not assign an
independent validation label or close the external learner-view gate.

## Repair generation 2 controller follow-up

Controller audit
`9768c1e824f3afcf1d3668dbf93c7ce0c7ee31a1783e44fc0e7ee791b2461985`
demonstrated that a physical task could logically exit, be reaped, reuse its
slot for a replacement, and then kill that replacement from a stale yield or
return. The repair adds PID ownership to every runtime context and retains the
physical `(slot, PID)` independently of `scheduler.current_slot`. Context saves
use the slot image only while both identities still match; otherwise they use a
dedicated discard image and dispatch the scheduler's selected replacement.

`sealed/reference_tests/runtime_reentrancy.c` covers stale yield and stale
return using the actual ARM context switch. Its bounded runner requires both
replacements and `NO-BUG`, and rejects continued outer execution and the prior
failure marker. This builder evidence remains subject to fresh independent
review and does not add a validation label.
