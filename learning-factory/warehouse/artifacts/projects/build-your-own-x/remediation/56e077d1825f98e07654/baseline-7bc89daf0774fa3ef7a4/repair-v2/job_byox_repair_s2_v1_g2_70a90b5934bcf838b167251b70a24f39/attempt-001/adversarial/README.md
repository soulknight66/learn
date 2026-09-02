# Adversarial validation plan

This evaluator-facing plan targets valid-looking inputs that cross representation
boundaries. It does not contain a candidate implementation.

The 12 machine-readable vectors in `cases/boundaries.json` cover:

- PID exhaustion and stale PID reuse after reaping;
- scheduler tables with duplicate identities or mismatched running/current state;
- a frame pool whose one-past end is exactly 2^32 versus one page beyond it;
- combined permission requests where only one requested bit is present;
- a valid translation whose final physical byte is `0xffffffff`;
- RAMFS offset-plus-length wrap, full-capacity create, zero-length null buffers,
  and scrub-before-reuse behavior.

`run_vectors.py` strictly checks the schema, rejects missing, duplicate, unknown,
or expectation-mismatched cases, and invokes `vector_runner.c` once for every
declared vector with an argv array and a five-second per-case bound. Each command
starts in a new process group. Timeout kills that complete group, waits for the
direct child, drains bounded output, and closes captured streams. The test target
first runs a deterministic helper whose descendant would write an escape marker;
the marker must remain absent after group termination. Run it with:

```sh
make -C adversarial clean test \
  PYTHON=/absolute/path/to/python3 \
  CC='/absolute/path/to/gcc -B/absolute/path/to/binutils/bin/'
```

The C runner copies complete object representations into unsigned-byte buffers
with `memcpy` before expected failures, then compares every byte afterward. It
also tests operations after state transitions rather than only from freshly
initialized state. Emulator adversarial work should stop QEMU with a bound and
retain the last serial marker for a task that returns, blocks the only runnable
task, or yields after another task exits.

These vectors were generated for this project. They are neither hidden grader
data nor evidence that fuzzing was performed; `MANIFEST.yaml` contains no
`FUZZED` label.
