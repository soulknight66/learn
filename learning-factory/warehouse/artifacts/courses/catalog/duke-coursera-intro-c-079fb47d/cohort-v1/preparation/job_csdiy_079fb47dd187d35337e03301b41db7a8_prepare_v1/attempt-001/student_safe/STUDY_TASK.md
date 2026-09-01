# Study task: an inspectable integer vector in C

*Artifact provenance: course-manager-authored from catalog-described C programming themes. Validation label: `LEARNER_SAFE_KICKOFF_PREPARED_NOT_VALIDATED`.*

Create a small C11 project named `intvec` that implements a heap-backed vector of `int`. Work in a Git repository and favor small, meaningful commits. Do not use an external container or collection library.

## 1. Define the public contract

Create `include/intvec.h` with these public types and operations (names and signatures are fixed so the work can be exercised consistently):

```c
#include <stddef.h>

typedef struct {
    int *data;
    size_t len;
    size_t cap;
} IntVec;

typedef enum {
    IV_OK = 0,
    IV_ERR_INVALID,
    IV_ERR_OOM,
    IV_ERR_BOUNDS,
    IV_ERR_OVERFLOW
} IvStatus;

void iv_init(IntVec *vec);
void iv_destroy(IntVec *vec);
IvStatus iv_reserve(IntVec *vec, size_t min_capacity);
IvStatus iv_push(IntVec *vec, int value);
IvStatus iv_insert(IntVec *vec, size_t index, int value);
IvStatus iv_remove(IntVec *vec, size_t index, int *removed_value);
IvStatus iv_get(const IntVec *vec, size_t index, int *out_value);
```

In `README.md`, document for every function:

- valid and invalid arguments;
- who owns any referenced storage before and after the call;
- what success changes;
- what each possible error means; and
- whether the vector is unchanged on failure.

The required public-boundary invariants are:

- `len <= cap`;
- `data == NULL` exactly when `cap == 0`; and
- elements at indices from zero through `len - 1` are initialized values owned by the vector.

`iv_init(NULL)` and `iv_destroy(NULL)` must be harmless. After initialization and after destruction, a non-null vector must be in the same empty state. All status-returning functions must reject a null vector. Output pointers are required for `iv_get`; `removed_value` is optional for `iv_remove`.

## 2. Implement defensively

Implement the component in `src/intvec.c`.

- Grow geometrically rather than reallocating on every push.
- Before any byte-size calculation or capacity growth, detect values that cannot be represented safely by `size_t` or allocated as an `int` array. Report `IV_ERR_OVERFLOW` without changing the vector.
- Report allocation failure as `IV_ERR_OOM` without losing the old allocation or changing observable vector contents.
- Treat insertion at `index == len` as valid. Other insertion indices greater than `len` are out of bounds.
- A get or remove at an index greater than or equal to `len` is out of bounds.
- Preserve element order during insertion and removal.
- Do not shrink capacity during removal.
- Do not read uninitialized memory, access storage outside its allocation, leak memory, double-free, or use freed storage.

Keep helper functions private to the implementation. Do not add global mutable state.

## 3. Build and test

Provide a `Makefile` with these targets:

- `all`: build `build/intvec_tests`;
- `test`: build and run the test executable;
- `debug`: build a debuggable test executable with compiler warnings enabled and optimization disabled;
- `sanitize`: build and run tests with AddressSanitizer and UndefinedBehaviorSanitizer if supported; and
- `clean`: remove generated build products.

Use a strict warning set supported by your compiler, including at least `-Wall -Wextra -Wpedantic`, and compile as C11.

Create `tests/test_intvec.c` using a lightweight test harness of your own. Each test must produce a deterministic pass/fail result, and the process must return nonzero if any test fails. Cover at least:

- initialization and repeated destruction;
- pushes across multiple growth events;
- reserving less than, equal to, and greater than current capacity;
- insertion at the front, middle, and end;
- removal at the front, middle, and end, both with and without an output pointer;
- gets at valid and invalid indices;
- invalid null arguments;
- preservation of state after bounds and overflow failures; and
- a mixed sequence checked against a simple fixed-array reference model.

You are not required to force the system allocator to return null, but your design and documentation must explain how the old vector survives that path.

## 4. Produce debugging evidence

Create `DEBUGGING.md`. Include exact commands and short, relevant output excerpts for all of the following:

1. A clean build and test run.
2. One GDB session on a temporary, genuine defect you introduced locally. Show a breakpoint or watchpoint, the observed state that identified the defect, and the subsequent fix. The final submitted source must contain the fix.
3. A Valgrind run with leak checking on `build/intvec_tests`. If Valgrind is unavailable, state that limitation and include a successful `make sanitize` run instead.
4. The final `git status --short` and a one-line Git log for the unit's commits.

Do not manufacture a transcript. Keep only enough output to make the commands and conclusions reproducible, and remove generated binaries before submission.

## 5. Explain and package the work

Add a short `DESIGN.md` that names the vector invariants, describes growth and error-state behavior, and states the time complexity of each operation. Include one paragraph on how this C representation differs from a garbage-collected or bounds-checked collection you have used.

Your submission contains:

```text
include/intvec.h
src/intvec.c
tests/test_intvec.c
Makefile
README.md
DESIGN.md
DEBUGGING.md
COMPREHENSION_RESPONSES.md
```

Copy each prompt number from `COMPREHENSION.md` into `COMPREHENSION_RESPONSES.md` and answer in your own words. Cite the relevant function, test, or debugging excerpt when a prompt asks about your implementation.

Before submitting, run the clean-build sequence from a fresh build directory state and check that the repository contains no binary, core dump, editor backup, credential, or unrelated artifact.
