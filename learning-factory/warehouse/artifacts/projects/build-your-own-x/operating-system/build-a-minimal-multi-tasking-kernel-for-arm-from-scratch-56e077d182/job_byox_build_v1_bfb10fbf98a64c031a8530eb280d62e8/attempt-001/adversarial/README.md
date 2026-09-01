# Adversarial validation notes

Independent validators should vary more than example values. Useful campaigns include:

- exhaust tasks, frames, files, and blocks in multiple interleavings, then verify exact reclamation;
- pass stale, zero, zombie, and recently reaped PIDs to every applicable API;
- probe addresses at page ends, `MK_USER_SIZE`, and overflowing length combinations;
- make a cross-page write fail on its last page and compare every earlier byte;
- replace files while full, shrink to zero, regrow, and use existing block memory as input;
- use callbacks that sleep, exit explicitly, yield, return invalid enum values, or kill peers;
- run with sanitizers and mutate operation sequences with a fixed recorded seed.

The executable adversarial cases are consolidated under sealed reference tests so expected outcomes
and solution-bearing checks do not become learner hints.
