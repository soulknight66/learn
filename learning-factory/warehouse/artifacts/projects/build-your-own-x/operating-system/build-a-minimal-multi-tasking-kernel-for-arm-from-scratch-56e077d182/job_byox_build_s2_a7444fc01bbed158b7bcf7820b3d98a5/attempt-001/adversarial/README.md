# Adversarial validation plan

This evaluator-facing plan targets valid-looking inputs that cross representation
boundaries. It does not contain a candidate implementation.

The machine-readable vectors in `cases/boundaries.json` cover:

- PID exhaustion and stale PID reuse after reaping;
- scheduler tables with duplicate identities or mismatched running/current state;
- a frame pool whose one-past end is exactly 2^32 versus one page beyond it;
- combined permission requests where only one requested bit is present;
- a valid translation whose final physical byte is `0xffffffff`;
- RAMFS offset-plus-length wrap, full-capacity create, zero-length null buffers,
  and scrub-before-reuse behavior.

An independent harness should snapshot complete structures before every expected
failure and compare every byte afterward. It should also perturb operation order
instead of testing APIs only from freshly initialized state. Emulator adversarial
work should stop QEMU with a bound and retain the last serial marker for a task
that returns, blocks the only runnable task, or yields after another task exits.

These vectors were generated for this project. They are neither hidden grader
data nor evidence that fuzzing was performed; `MANIFEST.yaml` contains no
`FUZZED` label.
