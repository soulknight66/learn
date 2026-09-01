# Study Task: Implement `vmwalk`

> Unit: `unit_kickoff_vmwalk_v1`  
> Artifact provenance: course-manager-authored from the supplied catalog snapshot; no external material is required.  
> Validation label: **PREPARED / LEARNER WORK NOT YET VALIDATED**

Build a portable C11 command-line program that reads a bounded trace, constructs the modeled mappings, evaluates access requests, and reports translations or modeled faults.

## Required submission

Use this layout:

```text
src/main.c
src/vmwalk.c
src/vmwalk.h
Makefile
tests/
DESIGN.md
COMPREHENSION_RESPONSES.md
evidence/build.log
evidence/test.log
evidence/SELF_CHECK.md
```

The executable must be `build/vmwalk`. It accepts exactly one argument:

```text
build/vmwalk TRACE_FILE
```

Use only the C standard library in the program. Put the trace and translation implementation behind a coherent interface declared in `src/vmwalk.h` and defined in `src/vmwalk.c`; keep `src/main.c` focused on CLI handling and orchestration. The program must not use a network service, invoke another program, or require downloaded packages.

## Trace language

A command is one of:

```text
map L1 L2 PPN PERMISSIONS
access MODE VIRTUAL_ADDRESS
```

Lexical rules:

- Input is ASCII text with LF or CRLF line endings. A final line without a line ending is allowed; any non-ASCII byte makes the trace invalid.
- Tokens are separated by one or more ASCII spaces or tabs. Leading and trailing spaces or tabs are allowed.
- A blank line is ignored.
- A line whose first character other than an ASCII space or tab is `#` is ignored. Inline comments are invalid.
- Keywords, modes, and permission letters are lowercase and case-sensitive.
- Hexadecimal numbers have a lowercase `0x` prefix followed by one or more hexadecimal digits. Digits `a`–`f` may be either case, extra leading zeroes are allowed, and signs are invalid.
- A logical line contains at most 128 bytes, excluding its CR/LF terminator. A trace contains at most 2,048 logical lines.
- Blank and comment lines count toward the 2,048-line limit and toward the one-based line number used in diagnostics.
- Every non-comment line must contain exactly the tokens shown by its command grammar.

Value rules:

- `L1` and `L2` are in `0x0` through `0xf`.
- `PPN` is in `0x00` through `0xff`.
- `VIRTUAL_ADDRESS` is in `0x0000` through `0xffff`.
- `MODE` is exactly one of `r`, `w`, or `x`.
- `PERMISSIONS` is a nonempty sequence of distinct characters drawn from `rwx`; order has no meaning.
- A pair `(L1, L2)` may be mapped only once.
- All `map` commands must appear before the first `access` command.
- A trace contains at most 256 mappings and 1,024 accesses.

An empty trace, a comments-only trace, and a map-only trace are valid and produce no output. The 16-by-16 key space and the no-duplicates rule inherently limit mappings to 256; a completely populated table must still be accepted.

Any violation makes the entire trace invalid. Validate the full trace before writing access results, so invalid input produces no standard output even if earlier lines were valid.

## Access behavior

For each access in a valid trace, split the 16-bit virtual address as specified in the course brief and look up `(L1, L2)`.

Write exactly one line per access. Hexadecimal addresses in output use a lowercase `0x` prefix and exactly four lowercase digits:

```text
OK <mode> <virtual-address> <physical-address>
FAULT <mode> <virtual-address> UNMAPPED
FAULT <mode> <virtual-address> PERMISSION
```

Preserve access order. Do not add headings, summaries, or debug text to standard output.

## Exit and diagnostic contract

- Return `0` for every valid trace, including a trace that produces modeled faults.
- Return `2` for invalid invocation or invalid trace input.
- Return `1` when the named file cannot be opened or an internal/resource failure prevents correct processing.
- An invalid trace must emit a concise standard-error diagnostic beginning with `line N:`, where `N` is the one-based logical line number.
- An invalid invocation must emit a concise usage diagnostic to standard error.
- Never report a guessed or partial result after a detected error.

## Build contract

`make clean all` must create `build/vmwalk` and compile all submitted C code with at least:

```text
-std=c11 -Wall -Wextra -Werror -pedantic
```

`make check` must run the deterministic local test suite, return nonzero on a failed check, require no network, and terminate without interactive input. Test automation may use submitted C11 code or the Python 3 standard library, but no third-party package. Keep generated build products under `build/`.

## Required test coverage

Include automated checks for:

- a successful translation with nonzero indices and offset;
- the lowest and highest virtual addresses;
- read, write, and execute access;
- an unmapped fault and a permission fault;
- two virtual pages that map to the same physical page;
- duplicate mappings and a mapping after the first access;
- malformed, signed, and out-of-range numeric tokens;
- malformed permissions and extra tokens;
- an overlong line, the total-line and access bounds, and a fully populated 256-entry map table;
- exact output formatting, no output for an invalid trace, exit `0` for valid traces, exit `2` for invalid input, and exit `1` for a nonexistent input path.

Tests must inspect behavior, not merely execute the program. Test inputs and expected results belong under `tests/`.

## Engineering note

Write `DESIGN.md` in at most 400 words. Identify:

- your table and parsed-access representations;
- at least one invariant and the code boundary that enforces it;
- how modeled faults, input errors, and internal failures remain distinct; and
- one deliberate omission that keeps the program within this unit's boundary.

## Evidence and stopping rule

From a clean tree, run `make clean all` and `make check`. Record the exact commands, tool versions, exit statuses, and unedited output in the two log files. In `evidence/SELF_CHECK.md`, state one of:

```text
SELF-CHECKED: both required commands returned zero
INCOMPLETE: <first failing command or precise blocker>
```

Learner-produced files never receive the `HARNESS-VALIDATED` label. Stop at six hours even if work remains; preserve the evidence and hand off the bounded state instead of adding unrequested features.
