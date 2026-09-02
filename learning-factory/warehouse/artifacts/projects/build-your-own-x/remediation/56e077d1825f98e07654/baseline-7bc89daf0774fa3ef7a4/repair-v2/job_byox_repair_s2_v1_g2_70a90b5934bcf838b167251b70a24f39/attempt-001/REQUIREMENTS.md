# Requirements

Normative words **MUST**, **MUST NOT**, and **SHOULD** describe candidate
behavior. Constants are declared in the starter headers.

## 1. Target and boot

- The kernel MUST be a freestanding 32-bit little-endian ARM ELF linked at
  `0x00010000` for QEMU `versatilepb` with an ARM926EJ-S-class CPU.
- Reset code MUST install an 8-byte-aligned supervisor stack, clear `.bss`, and
  call `kernel_main` without relying on firmware initialization.
- UART output MUST use PL011 at `0x101f1000` and translate each newline to CRLF.
- A full run MUST emit these markers in order: `LF-KERNEL boot`, `mmu: on`,
  `vm: ok`, `ramfs: ok`, `tasks: ABABAB`, and `PASS reference`.

## 2. Processes and scheduling

- The scheduler MUST represent `UNUSED`, `READY`, `RUNNING`, `BLOCKED`, and
  `ZOMBIE` as distinct states and admit at most `LF_MAX_TASKS` slots.
- PIDs MUST be nonzero and monotonically increase until the documented 32-bit
  exhaustion case. Slots MAY be reused only after a zombie is explicitly reaped.
- At most one task may be `RUNNING`. `rotate` MUST requeue a running current task,
  then select the first ready slot strictly after it, wrapping once. If it is the
  only runnable task, it selects itself. If none is ready, current becomes none.
- Blocking and exiting MUST apply only to the running current task. Unblock MUST
  accept only a blocked PID; reap MUST accept only a zombie PID.
- The ARM runtime MUST preserve r4-r11, sp, and lr across a cooperative switch.
  A task return MUST be equivalent to an explicit exit, never a branch into
  arbitrary stack data.

## 3. Frames and virtual mappings

- The frame pool MUST manage 4 KiB frames using fixed metadata. Initialization
  MUST reject a misaligned base, zero count, or count above `LF_MAX_FRAMES`.
- Allocation MUST return the lowest free frame. Retain MUST detect reference
  overflow; release MUST reject unallocated and out-of-pool addresses.
- A mapping MUST have aligned virtual and physical bases, a nonzero subset of
  `READ`, `WRITE`, and `EXEC`, and a unique virtual page. Mapping-table failure
  MUST NOT partially mutate the address space.
- Translation MUST add the page offset without overflow and deny an access unless
  every requested permission is present. Unmap MUST reject absent pages.
- Frame-pool and address-space initialization MUST canonicalize their complete
  object representations, including padding bytes, so later raw-byte snapshots
  have a deterministic baseline.
- The board MMU setup MUST use a 16 KiB-aligned ARM short-descriptor L1 table,
  establish identity mappings for kernel RAM and required MMIO before enabling
  translation, and invalidate stale TLB state.

## 4. RAM filesystem

- The filesystem MUST hold at most `LF_RAMFS_MAX_FILES` regular files, each with
  a unique nonempty name of at most `LF_RAMFS_NAME_MAX` bytes and at most
  `LF_RAMFS_FILE_MAX` data bytes. Names are exact byte strings terminated by NUL;
  `/`, `.` and `..` have no special meaning in this flat filesystem.
- Create MUST reject duplicates and overlong names. Read and write MUST reject a
  null buffer when their length is nonzero and MUST detect offset-plus-length
  overflow before checking capacity.
- A successful write MAY create a zero-filled hole and MUST grow size to the
  greatest written end. Reads stop at end of file and report the byte count.
- Unlink MUST clear all file bytes and metadata before making a slot reusable.
- Every rejected operation MUST leave the complete filesystem byte-for-byte
  unchanged.
- Initialization and unlink MUST zero the complete object or file-record
  representation, including padding bytes. Padding is part of the normative
  byte state for this bounded filesystem.

## 5. Verification constraints

- Portable tests MUST compile with C11, `-Wall -Wextra -Werror -pedantic`, and
  sanitizers where the host supports them.
- Mutation snapshots MUST copy object representations into unsigned-byte
  buffers with `memcpy`; structure assignment is not portable snapshot
  evidence because padding values may be unspecified.
- Kernel builds MUST use `-ffreestanding`, must not link a hosted C library, and
  MUST have no unresolved symbols in the final ELF.
- Serial success text is not proof by itself: host tests and independent
  validation remain required.

## Non-goals

Interrupt-driven preemption, userspace exception return, demand paging, storage
persistence, directories, concurrent filesystem calls, multicore support, and
production hardening are outside the required core.
