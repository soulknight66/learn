# Design

## Observable contract

The command accepts zero or one argument. With zero it consumes standard input;
with one it opens that exact name in binary mode. It emits `total N`, then only
nonzero byte counters in ascending `00` through `FF` order, with one newline per
line. Success is status 0 with an empty diagnostic stream. Too many arguments
produce the specified usage line, no standard output, and status 2. All other
detected failures produce a `bytehist:` diagnostic and status 1.

No report begins until input has reached end-of-file successfully and an owned
input stream has closed successfully. Consequently, every input failure leaves
standard output empty. Once reporting starts, an output failure may leave a
partial report, but it is never returned as success.

## Module contract and boundary

`include/bytehist.h` exposes an opaque `ByteHistogram`. `bytehist_create`
returns an empty histogram owned by the caller, and `bytehist_destroy` releases
it. `bytehist_add` atomically adds a nonnegative occurrence count to one byte;
it returns false without mutation if either affected unsigned 64-bit quantity
would overflow. The observer functions return the total and a selected byte's
count. Callers provide a non-null histogram, and only the module mutates its
state.

This boundary keeps allocation, representation, invariant preservation, and
range checks out of the CLI. Conversely, the module knows nothing about files,
arguments, formatting, diagnostics, or exit codes. A later presentation format
can reuse the module and input loop while replacing only report emission and
format selection.

## Invariants and mutation

After creation and after every successful update:

- every counter and the total are representable as `uint64_t`;
- `total` equals the sum of all 256 counters (mathematically, without wrap);
- a counter equals the number of accepted occurrences of its byte value; and
- `total` equals the number of all accepted byte occurrences.

Creation establishes the invariants with zero-filled state. `bytehist_add`
checks both additions before mutating either field, so success preserves all
invariants and failure preserves the prior state. During normal input,
`src/main.c` stores `fread` data in an `unsigned char` array and adds each
accepted element once. The invariants therefore hold after each byte, at every
read boundary, at end-of-input, and while the immutable report is produced.

## Streaming and failure policies

The input loop uses a fixed 4096-byte buffer, so memory consumption is
independent of input size. A positive `fread` result is progress and all
returned elements are consumed. The loop then checks `ferror` before `feof`;
an error suppresses the report, while EOF completes input. A short read with
neither terminal condition continues. A zero-byte result with neither flag is
treated as a no-progress input failure rather than looping forever.

Files opened by the command are closed before reporting, and a close failure is
an input failure. Standard input is borrowed and is not closed. On every
pre-report failure the histogram and any owned stream are released. Reporting
checks every `fprintf` and the final `fflush`; supported systems also ignore
`SIGPIPE` so a closed pipe is observed as a normal output error. Any output
error diagnoses failure and returns status 1.

For range safety, each module update checks the requested occurrence count
against both `UINT64_MAX - total` and `UINT64_MAX - selected_count` before
mutation. A failed check reaches the CLI as `READ_COUNT_OVERFLOW`; it emits no
report and returns status 1. The bulk-count parameter lets the module's
otherwise impractical near-limit behavior be tested deterministically.
