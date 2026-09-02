# Reference design

This is the sealed rationale for the independently generated implementation.

## Boot and target boundary

QEMU loads the ELF entry at `0x00010000`. `_start` masks IRQ/FIQ, installs a
linker-reserved supervisor stack, clears the complete `.bss` interval, and calls
C. The linker emits separate RX and RW load segments and marks the stack
non-executable. PL011 is polled because interrupts are outside the core scope.
Newlines are normalized at the character boundary so every caller gets CRLF.

Semihosting occurs only after `kernel_main` returns. It provides deterministic
emulator termination and is not on any kernel feature path.

## Scheduler policy

The policy table owns task identity and lifecycle; the runtime owns ARM register
images and stacks. This keeps host tests architecture-neutral.

The invariant is:

- every unused slot has PID zero and no entry;
- every live slot has a unique nonzero PID and a non-null entry;
- `current_slot == -1` exactly when no slot is running;
- otherwise `current_slot` names the sole running slot.

All public mutations first validate that invariant. Selection searches exactly
one wrap, beginning after the old slot. `rotate` converts the old running slot to
ready before searching. Block and exit retain the old index only as the search
origin, publish their terminal/intermediate state, clear current, and then
select. Reaping alone makes a slot unused. PIDs are monotonically allocated;
after PID `UINT32_MAX`, zero is an exhaustion sentinel rather than a wrapped PID.

The ARM context is ten contiguous words: r4-r11, sp, lr. These are precisely the
callee-saved registers plus continuation state for the ARM procedure-call ABI.
A new context uses an aligned top-of-stack and a non-returning bootstrap as lr.

Logical selection is not assumed to identify the physical frame currently on
the CPU. The runtime records that frame as `(executing_slot, executing_pid)`,
and every per-slot register image has a `context_pids` owner. The monotonically
allocated PID acts as the slot incarnation. A bootstrap captures its pair before
calling the entry point and uses that captured identity when the entry returns.

Normally the physical pair equals the scheduler's sole running entry. If policy
APIs exit and reap that task, reuse its slot, and select a replacement before
the old frame reaches a runtime boundary, the pairs differ. Yield and exit then
honor the already-selected runnable identity rather than rotating it. The old
registers are written to a discard context unless the old PID still owns its
slot and register image, so they cannot overwrite the replacement's initialized
context. If the old task still exists but policy selection moved elsewhere, its
own context remains a safe save destination. A normal or stale task return uses
the same identity-aware dispatch and ultimately switches either to the selected
task or the saved boot context.

## Virtual memory layers

The portable frame pool is an ownership ledger, not byte storage. Initialization
uses 64-bit arithmetic to prove the managed half-open range fits in the 32-bit
physical space. The first zero refcount is the deterministic allocation choice;
retain/release accept only aligned in-range allocated frames.

Each software address space has sixteen 4 KiB mappings. Map validates both
bases, the permission subset, uniqueness, and available capacity before writing
one slot. Translation finds the page, verifies every requested permission, and
only then adds the offset. The Boolean result keeps physical `0xffffffff` from
being confused with an error sentinel.

Board bring-up uses a 16 KiB L1 short-descriptor table. It identity-maps 128 MiB
of RAM and sixteen MiB of the `0x10000000` device region, installs TTBR and domain
state, invalidates the unified TLB, drains writes, and finally sets SCTLR.M.
Those section mappings are deliberately broader than the per-process software
maps. Building hardware L2 tables and switching TTBR per process is an extension.

## RAM filesystem

The filesystem is a flat table of eight inline records. Names and contents never
refer to external storage, so there is no lifetime ambiguity. Create validates
the bounded NUL-terminated name, checks duplicates and finds capacity before
touching the chosen unused slot; `used` is published last. Write validates file,
pointer, integer addition, and capacity before zero-filling a hole and copying.
Read verifies overflow even when the offset is beyond EOF. Unlink zeros name,
data, and size before clearing `used`.

This sequencing establishes failure atomicity for a single-threaded kernel.
Interrupt or multicore concurrency would require a separate synchronization and
publication design.

## Demonstration path

The emulated boot enables translation, exercises a shared physical frame through
two software spaces with different permissions, round-trips a RAMFS file, and
then starts two independent stacks. Each task emits its marker three times and
yields, so strict after-current selection produces `ABABAB`. A returned task is
converted to a zombie, and the final return restores the boot continuation.
