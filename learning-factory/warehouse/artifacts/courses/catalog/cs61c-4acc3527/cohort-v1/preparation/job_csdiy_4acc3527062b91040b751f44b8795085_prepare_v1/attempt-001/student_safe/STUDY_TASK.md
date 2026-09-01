# Study Task: Build a Verified Integer Index

> **Artifact label:** Manager-authored learner task; awaiting worker-harness validation. Completion applies only to the bounded kickoff unit.

## Goal

Build `rankq`, a small C11 command-line tool backed by a reusable integer-index library. The program loads signed 32-bit integers, stores a sorted copy, and answers lower-bound membership queries. The familiar search problem lets you concentrate on software contracts, ownership, parsing, diagnostics, and reproducible verification.

Work only in your assigned attempt workspace. Do not use code from external course assignments or student repositories.

## Required project layout

Create at least these files:

```text
include/int_index.h
src/int_index.c
src/rankq.c
tests/test_int_index.c
tests/test_cli.py
Makefile
README.md
DESIGN.md
TESTING.md
COMPREHENSION_RESPONSES.md
```

Do not submit binaries, object files, sanitizer output, downloaded course material, or secrets as source artifacts.

## 1. Library contract

Expose the following names from `include/int_index.h`. You may add documentation and private helpers, but do not change these public names or their meanings.

```c
typedef enum {
    INT_INDEX_OK = 0,
    INT_INDEX_INVALID_ARGUMENT,
    INT_INDEX_TOO_LARGE,
    INT_INDEX_NO_MEMORY
} int_index_status;

typedef struct {
    int32_t *values;
    size_t length;
} int_index;

void int_index_init(int_index *index);
int_index_status int_index_build(
    int_index *out,
    const int32_t *input,
    size_t length
);
size_t int_index_lower_bound(const int_index *index, int32_t key);
bool int_index_contains(const int_index *index, int32_t key);
void int_index_destroy(int_index *index);
```

Include the standard headers needed by users of this header. The interface has these rules:

- `int_index_init` establishes the canonical empty state: `values == NULL` and `length == 0`.
- `int_index_build` requires `out` to point to an initialized empty index. `input` may be `NULL` only when `length` is zero.
- A successful build owns a newly allocated, ascending sorted copy of the input. It retains duplicates and never changes the caller's input.
- An empty successful build remains in the canonical empty state.
- Before allocating, a build must reject a byte-count overflow with `INT_INDEX_TOO_LARGE`.
- On every reported failure, `out` remains in the canonical empty state.
- `int_index_lower_bound` returns the first index whose value is greater than or equal to `key`, or `length` if there is no such element. Its running time after construction must be `O(log n)`.
- `int_index_contains` reports membership without reading outside the array.
- `int_index_destroy` releases owned storage and restores the canonical empty state. Repeated destruction of an initialized index is safe.
- Query functions require a non-null pointer to a valid initialized index. Document this precondition; do not invent a sentinel return value.

Use only well-defined C behavior. A comparator must work for the full `int32_t` range. Do not rely on signed overflow, invalid pointer arithmetic, zero-filled allocations, or a particular byte order.

## 2. Command-line contract

The executable interface is:

```text
rankq DATA_FILE QUERY [QUERY ...]
```

`DATA_FILE` is a text file with at most 1,000,000 records. Each nonblank logical line contains exactly one base-10 signed integer in the `int32_t` range, with optional leading/trailing spaces or tabs and an optional leading `+` or `-`. Accept LF and CRLF line endings and a final line without a newline. Ignore blank lines. Reject:

- a partial number or extra non-whitespace text;
- a value outside the `int32_t` range;
- a logical line longer than 200 bytes, excluding its line ending; or
- more than 1,000,000 integer records.

Each `QUERY` must consist entirely of one base-10 signed integer in range, with an optional leading sign. Validate every query and the complete data file before writing any result to standard output.

For each query, write exactly one line in argument order:

```text
<canonical-query>\t<zero-based-lower-bound-index>\t<present-or-absent>\n
```

Here `present-or-absent` is the literal word `present` or `absent`; the query is printed in canonical decimal form. Diagnostics go to standard error. Use these exit statuses:

| Status | Meaning |
|---:|---|
| 0 | All requested results were produced. |
| 64 | Usage error or invalid query argument. |
| 65 | Malformed, overlong, or oversized data input. |
| 66 | Data file could not be opened or read. |
| 70 | Allocation failure or violated internal invariant. |

Close files and release every owned allocation on every exit path. Do not use a shell command, temporary downloaded input, global mutable state, or network access.

## 3. Build contract

The default `make` target must build `rankq`. Also provide:

- `make test`, which rebuilds as needed and runs both the C unit test and deterministic CLI integration tests;
- `make sanitize`, which builds with AddressSanitizer and UndefinedBehaviorSanitizer and runs the same exercised behaviors; and
- `make clean`, which removes only the named build products created by this project.

Use separate compilation for the library and CLI. The ordinary build must use C11 and, at minimum, `-Wall -Wextra -Wpedantic -Wconversion -Werror`. Keep `CC`, `CPPFLAGS`, `CFLAGS`, and `LDFLAGS` override-friendly. Tests must use no network service, randomness, clock, locale-dependent expectation, or pre-existing machine file.

The Python integration test must use only the Python standard library. Launch processes with argument arrays, a bounded timeout, and captured output—never a shell string. Create test inputs in a temporary directory and remove them normally.

## 4. Required verification

Your C unit tests must exercise, at minimum:

- an empty index, a singleton, already sorted and reverse-sorted inputs;
- duplicate values and queries on both sides of a duplicate run;
- `INT32_MIN` and `INT32_MAX`;
- present and absent keys before, within, and after the stored range;
- preservation of the input array;
- failure for each invalid argument that the public build function can report without exhausting real memory; and
- destruction restoring the canonical empty state, including repeated destruction.

Your CLI tests must exercise successful multi-query output, blank lines, whitespace, CRLF, a missing final newline, malformed and out-of-range data, an overlong line, excess records, a missing file, bad usage, and invalid query text. Check exit status, standard output, and relevant standard-error behavior. Generate large boundary fixtures during the test rather than checking them into source control.

Run the strict ordinary build and the sanitizer target. Investigate warnings, crashes, leaks, and mismatches; do not merely paste output.

## 5. Engineering evidence

In `README.md`, record build/test commands, the executable contract, and one small invocation a reviewer can reproduce with their own local input.

In `DESIGN.md`, record:

- module responsibilities and why the public/private boundary is placed there;
- the index invariant before and after each public operation;
- an ownership table covering the index allocation, parser storage, file handle, and test fixtures;
- failure-path cleanup and how error categories remain distinguishable;
- integer conversion and allocation-overflow risks; and
- construction/query time and space costs.

In `TESTING.md`, record the compiler and runtime tool versions, exact commands run, and a test matrix with case, expected property, observed result, and evidence location. Summarize sanitizer results and remaining limitations. Your report helps review, but the validator will rerun checks independently.

Answer every prompt in `COMPREHENSION.md` in `COMPREHENSION_RESPONSES.md`. Use your own implementation as evidence and cite relevant file and function names. Do not search for or include an examiner rubric.

## Stop condition

Stop when the listed artifacts are complete and locally verified. Do not start a later CS61C topic or claim course completion.
