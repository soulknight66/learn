# Debugging exercises

These exercises describe symptoms without revealing repairs. Corresponding evaluator answers live
under the root sealed tree.

1. **Frame leak on duplicate map** (`frame_leak/README.md`): isolate an ordering bug spanning the VM
   table and frame allocator.
2. **Skipped process after block** (`scheduler_cursor/README.md`): distinguish current ownership
   from round-robin history.

For each exercise, write the smallest failing operation sequence first, state the violated
invariant, and only then propose a patch.
