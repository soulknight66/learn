# Adversarial testing exercise

This exercise file contains prompts only. If it is separately assigned to a learner, its sealed
subdirectory must remain hidden.

Build a framework-free Java test program that drives only the public API. Give
each scenario a descriptive name, check byte contents as well as offsets, and
make every run deterministic.

## Required attacks

1. Ownership: mutate an input array after local and replicated append; mutate an
   array returned by LogRecord.value; retain an old read result and try to affect
   a later read.
2. Boundaries: cover an empty log, zero-size reads, reads at the visible end,
   reads one beyond it, negative arguments, and limits larger than the remainder.
3. Rejected write: snapshot the watermark and every replica end, remove enough
   ISR members to reject append, attempt it, and prove that the attempted value
   appears nowhere.
4. Ordering: construct replicas in a deliberately unsorted order, fail leaders
   repeatedly, and verify that elections are deterministic without assuming set
   iteration order.
5. Stale-first recovery: let one replica miss committed records, remove every
   current leader candidate, recover the stale replica before an up-to-date one,
   and test both safety and eventual repair.
6. Idempotence: repeat failure and recovery calls at each interesting point and
   compare all observable state.
7. State-machine trace: generate at least 1,000 commands from a fixed seed. Keep
   a simpler oracle for availability, ISR, committed bytes, leader eligibility,
   and replica ends. Compare after every command, including expected exceptions.

For each failure found, report the smallest replayable command trace, expected
state, actual state, and violated requirement. Do not use sleeps, wall-clock
deadlines, reflection, sealed code, or implementation-specific fields.

Threaded stress is optional because concurrency is not necessary to solve the
public exercise. If attempted, state the thread-safety property being tested and
record enough information to check whether the result has a legal sequential
ordering.
