# Debugging exercises

## DBG-1 — Lost runnable process

A scheduler implementation sets the old runner to `Ready`, selects the next
PID with `pop_front()?`, and only then appends the old PID. Explain why the `?`
can lose scheduler state and why the order violates the specified rotation.
Write the smallest test that distinguishes it from R2.3.

## DBG-2 — Leaked intermediate frame

An Sv39 mapper allocates and links a level-one table, then returns
`OutOfFrames` when allocating level zero. Allocator counts differ after the
error, although translation still says `NotMapped`. Identify every state item
that rollback must restore and propose a failure-injection matrix.

## DBG-3 — Partial namespace mutation

A filesystem removes the parent directory entry before checking whether the
target directory is empty. The function returns `DirectoryNotEmpty`, but the
subtree is no longer reachable. Describe a validate/reserve/publish ordering
that makes the error atomic.

Answer independently before consulting evaluator feedback. The corresponding
solutions live under the factory-sealed tree, not in this directory.
