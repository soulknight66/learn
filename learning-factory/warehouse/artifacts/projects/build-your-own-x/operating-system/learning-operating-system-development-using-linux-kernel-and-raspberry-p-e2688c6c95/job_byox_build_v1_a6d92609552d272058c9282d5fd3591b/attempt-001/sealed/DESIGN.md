# Sealed design rationale

## Representation

The reference uses one value-type `pebble_kernel_t`. Fixed tables make ownership visible and allow tests to compare the entire state before and after a failing call. Every record is zeroed before first use and after release; zero is therefore the canonical unused representation.

PIDs and slots are deliberately separate. Creation chooses the lowest free slot for deterministic allocation, while `next_pid` only increases. A reaped slot can hold a new process without making a stale PID valid again.

## Scheduler

The scheduler holds a cursor rather than searching after the currently running slot. It demotes the current process, scans once from the cursor, and advances the cursor only after a selection. Blocking and exiting clear `current_slot` immediately. This keeps the invariant “the slot is `-1`, or it names the sole running process” true between every pair of API calls.

Ticks advance on idle scheduling calls because the contract models attempted quanta, not executed work. A saturated tick counter is rejected before mutation to avoid unsigned wrap.

## Page ownership and copy-on-write

An absent page-table entry is all zero. A present entry holds one frame index and access flags. Ordinary mapping assigns the lowest free frame and zeroes its complete record before setting a reference count.

Fork performs resource validation first. Writable mappings lose `WRITE` and gain `COW` in both processes; read-only mappings are shared without `COW`. Each mapping contributes exactly one reference. The flags distinguish a deliberately read-only mapping from a temporarily protected mapping that may become writable after a split.

A write has three phases:

1. Validate the complete address range and permissions.
2. Count shared copy-on-write pages and compare that count with all free frames.
3. Split in virtual-page order using the lowest free frame, then copy user bytes.

Because phase two reserves capacity logically, phase three cannot encounter ordinary exhaustion. A copy-on-write page with one reference is made writable in place. This preserves isolation while avoiding a needless copy after the peer exits.

## Filesystem transactions

Names are bounded before any string operation. Open validates the process, flags, descriptor capacity, file lookup, and file capacity before creating or truncating. Only read/write mode bits are stored in a descriptor; creation and truncation are one-shot request bits.

Truncation resets every descriptor cursor for that file. Real Unix open descriptions may retain offsets beyond the new end-of-file; this smaller model instead maintains its stated cursor-within-file invariant after every successful call.

File bytes and namespace live in a file record. Cursor and access mode live in descriptors. Fork copies descriptor values and increments open counts, so parent and child start at the same cursor but then move independently. This is intentionally simpler than POSIX open-file descriptions and is stated in the learner contract.

Writes are all-or-error at the capacity boundary. Unlink refuses open files instead of implementing tombstones. Exit closes descriptors before leaving a zombie record.

## Invariant oracle

`pebble_check()` treats page mappings and descriptors as primary edges. It derives frame references and file open counts from those edges, checks stored counts exactly, and checks indices before following them. It also requires canonical zero representations for unused records and free frames. Diagnostics identify the first violation in a stable traversal order.

The checker is intentionally read-only and allocation-free so tests can call it after every generated operation. It is not a repair function.
