# Code-review exercises

## REV-1 — Permission predicate

Review this proposed write check:

```rust
if flags.intersects(PteFlags::READ | PteFlags::WRITE) { allow(); }
```

List the access-control failures, including user/kernel separation, and give a
truth table for read, write, and execute requests.

## REV-2 — Unmap reclamation

A patch frees the mapped data frame inside `unmap`, then frees every table on
the walk unconditionally. Review it for ownership violations, shared-prefix
damage, allocator mismatch, and failure atomicity. Specify tests that expose
each defect.

## REV-3 — Path normalization

A patch silently normalizes repeated `/`, removes `.`, and resolves `..` before
creating an inode. Compare this to R5.2. Discuss aliasing, boundary checks, and
why reject-only syntax simplifies all-or-nothing mutation.

Evaluator answers are stored only under `sealed/review_exercises/`.
