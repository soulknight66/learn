# Kernel core requirements

The words **must**, **must not**, and **exactly** are normative. `starter/include/tinyarm.h` defines
the public ABI and fixed capacities. All functions run synchronously on one simulated CPU.

## 1. General behavior

- Kernel operations must not allocate dynamic memory, perform host I/O, or use global mutable state.
- A function receiving a null required pointer returns `MK_ERR_INVALID` unless its return type cannot
  represent an error; query functions document their sentinel values in the header.
- Failed mutating calls must leave kernel state unchanged unless a requirement explicitly says
  otherwise.
- Fixed resources are selected by lowest array index. PIDs are monotonically assigned starting at 1
  and are not slot numbers.
- Public enum values and structure fields are part of the exercise ABI and must not be reordered.

## 2. Initialization and process lifecycle

`mk_init(kernel, quantum)` accepts quanta 1 through `MK_MAX_QUANTUM`. It clears the complete kernel,
sets simulated time to 0, sets the next PID to 1, records the quantum, sets no current task, and
formats an empty filesystem. Invalid arguments do not initialize the object.

`mk_spawn` requires a non-null step function and claims the lowest `MK_TASK_UNUSED` slot. The new
task is `MK_TASK_READY`, owns no pages, and receives the next PID. When no unused slot or PID remains,
it returns 0. A zombie slot is not reusable until reaped.

The legal lifecycle is:

```text
UNUSED -> READY -> RUNNING -> READY
                   |   |
                   |   +-> BLOCKED -> READY
                   +------> ZOMBIE -> UNUSED (reap)
```

Killing or exiting a live task immediately makes it a zombie, records its exit code, cancels a
current selection if necessary, and frees all of its mapped frames. `mk_reap` succeeds only for a
zombie; it optionally returns the exit code and clears that slot to `UNUSED`.

## 3. Scheduler and time

One successful `mk_tick` represents one scheduler interval:

1. At the current time, wake every blocked task whose `wake_tick <= now`.
2. Continue a valid running task, or scan circularly starting just after the last selected slot for
   the next ready task.
3. If a task is selected, invoke its step function exactly once and increment its `steps` counter.
4. Apply the callback result if the callback left the task running: `MK_STEP_EXIT` exits with code 0,
   `MK_STEP_YIELD` returns it to ready state, and `MK_STEP_CONTINUE` consumes one quantum unit. A
   quantum reaching zero returns it to ready state. Any other result exits with `MK_ERR_STATE`.
5. Advance `now` by exactly one.

Selection resets `quantum_left` to the configured quantum. Circular selection and retention during
an unexpired quantum make scheduling deterministic. If tasks are blocked but none is ready, a tick
is an idle interval and still advances time. If no ready, running, or blocked task exists,
`mk_tick` returns `MK_ERR_NOT_FOUND` without advancing time.

`mk_sleep_current(delay)` accepts only a running current task, delay greater than zero, and an
addition that does not overflow `uint64_t`. It blocks that task until `now + delay`. Because waking
happens at the start of a tick, a task sleeping at time 3 for 2 can next run during the tick that
starts at time 5.

`mk_run(kernel, limit)` performs at most `limit` successful ticks and stops early when no live task
remains. It returns the number performed. A zero limit changes nothing.

## 4. Virtual memory model

Each live task owns `MK_USER_PAGE_COUNT` virtual pages beginning at address zero. A PTE maps one
virtual page to one of the shared physical frames and holds any nonempty combination of
`MK_VM_READ` and `MK_VM_WRITE`.

- `mk_vm_map` requires a page-aligned address inside the user range, valid flags, an unmapped page,
  and a free frame. It selects the lowest free frame and zero-fills it before publishing the PTE.
- `mk_vm_unmap` requires a mapped, page-aligned user address. It clears and releases the frame.
- `mk_vm_read` and `mk_vm_write` may cross pages. Before copying anything, they must validate the
  PID, buffer, full non-overflowing range, every mapping, and the needed permission on every page.
  Consequently a failing write cannot partially modify an earlier page.
- A zero-length copy performs no buffer access and succeeds for a live PID when
  `virtual_address <= MK_USER_SIZE`.
- Task exit and kill release all owned frames. Newly allocated and newly freed frames contain zeroes.

## 5. Flat RAM filesystem

The filesystem has one root directory, fixed inodes, fixed-size blocks, and at most
`MK_FS_DIRECT_BLOCKS` per file. Valid paths are `/` followed by 1 to `MK_PATH_MAX` ASCII letters,
digits, `.`, `_`, or `-`; additional slashes are invalid.

- `mk_fs_create` creates an empty file in the lowest free inode. Duplicate paths return
  `MK_ERR_EXISTS`.
- `mk_fs_write` replaces the complete contents of an existing file. The maximum length is
  `MK_FS_MAX_FILE_SIZE`. It reuses that file's existing direct blocks in order, allocates any extra
  blocks by lowest free index, zero-fills every retained/allocated destination block, and frees
  unneeded trailing blocks. The input may alias existing filesystem storage. It must be staged before
  mutation. If validation or capacity checks fail, old bytes, size, and allocation remain unchanged.
- `mk_fs_read` copies up to the requested capacity starting at `offset`, stores the copied length in
  `out_read`, and returns success with zero bytes when the offset is at or beyond EOF.
- `mk_fs_stat` reports the exact byte size. `mk_fs_unlink` releases all blocks and the inode.
- Formatting clears inode metadata, allocation maps, and block bytes.

No persistence across `mk_init` is claimed; this component models filesystem invariants in RAM.

## 6. ARM milestone and exclusions

The host API models the deterministic policies to connect to an ARMv7-A port. The optional bare-metal
milestone must establish a stack, clear `.bss`, save and restore callee-saved registers at cooperative
switch points, and drive at least two independent stacks on QEMU's `virt` machine.

Actual MMU page-table programming, exception return, timer preemption, userspace privilege,
persistent storage, SMP, networking, and production hardening are out of scope. Do not represent the
host page table model as hardware isolation.

## 7. Acceptance

The starter library must compile with strict C11 warnings. A completed submission must pass public
tests and independent tests that cover exhaustion, stale PIDs, overflow, cross-page failures,
reclamation, filesystem atomicity, and deterministic ordering. Sanitizer-clean host execution is
expected where sanitizers are available. ARM execution is assessed only when the required external
tools are present.
