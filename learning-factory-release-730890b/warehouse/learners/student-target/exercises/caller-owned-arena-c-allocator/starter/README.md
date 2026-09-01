# Starter

Implement `allocator.c` against `../include/allocator.h`. A first milestone is one aligned
free block plus allocation; then add split, exact-pointer free, coalescing, resize, overflow
handling, statistics, and an invariant checker. Compile against the public contract with the
same warning policy documented in `environment/README.md`. The caller-owned harness acquires
effective-type-compatible backing storage; your allocator must not allocate its own arena.
Public tests are intentionally incomplete; add tests before revealing sealed material.
