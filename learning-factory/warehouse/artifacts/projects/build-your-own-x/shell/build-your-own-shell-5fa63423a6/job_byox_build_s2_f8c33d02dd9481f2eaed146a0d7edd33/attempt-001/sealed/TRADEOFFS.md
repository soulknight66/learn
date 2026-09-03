# Tradeoffs and alternatives

## One-pass lexer versus token slices

The reference allocates completed word strings as it lexes. Borrowed slices would reduce allocation but cannot naturally represent quote removal, escapes, or concatenated fragments. The explicit copies make ownership and tests simpler at modest cost for the 4096-byte input limit.

## Iterative pipe creation versus all pipes up front

Holding only the previous and next pipe reduces descriptor pressure from O(number of stages) in the parent to a constant. Creating all pipes first can make child indexing visually simpler, but it magnifies cleanup work and fails earlier under a low descriptor limit.

## Recorded PIDs versus waiting on the group

Waiting for each recorded PID makes it straightforward to return the last syntactic stage's status. `waitpid(-pgid, ...)` naturally reports completion order and stopped state, but then the shell needs a PID-to-stage map. A full job table would use group-oriented event collection plus persistent per-process state.

## Minimal job tracking

The implementation creates correct process groups and performs terminal handoff, but it does not expose `jobs`, `fg`, or `bg`. Retaining stopped groups without a selection interface is incomplete for a daily-use interactive shell. Killing stopped jobs automatically would avoid retention but be surprising; adding a real job table is the preferable production direction.

## `fork`/`execvp` versus `posix_spawnp`

`fork` makes descriptor and process-group mechanics visible and is widely suitable for this learning goal. `posix_spawnp` can be safer in multi-threaded programs and may avoid costly address-space duplication, but its file-action and process-group interfaces hide some of the exact lifecycle being taught.
