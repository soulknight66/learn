# Sealed implementation review

## Review scope

The review covered integer boundaries, table state transitions, failure
atomicity, freestanding linkage, ARM ABI context layout, MMU enable ordering,
serial evidence, and learner/reference isolation.

## Resolved findings

- **High — task return continuation:** New stacks have no caller. The runtime now
  enters a non-returning bootstrap, and normal task return invokes the zombie
  transition rather than consuming arbitrary stack data.
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
