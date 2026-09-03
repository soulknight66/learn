# Debugging exercises

## 1. Scheduler cursor

Symptom: after the process in slot five blocks, slot zero repeatedly wins even though slot six is
ready. Record the cursor and all process states immediately before scheduling. Identify which state
update discarded the scan origin and write a three-process regression test.

## 2. Exit leaks a frame

Symptom: mapping a recently released frame for another process returns `CAIRN_ERR_BUSY` after the
owner exits. Inspect both ownership views before and after exit. Determine whether cleanup touched only
the process mapping or only the reverse frame table, then test multiple mappings.

## 3. Validator crashes on corrupt input

Symptom: a sanitizer reports an out-of-bounds inode access when a descriptor's `inode_slot` is 999.
Trace the order of predicates in the descriptor invariant. Design the check so short-circuit behavior
prevents the index operation.

Resolutions are isolated under the corresponding exercise directories in `sealed/debugging/`.
