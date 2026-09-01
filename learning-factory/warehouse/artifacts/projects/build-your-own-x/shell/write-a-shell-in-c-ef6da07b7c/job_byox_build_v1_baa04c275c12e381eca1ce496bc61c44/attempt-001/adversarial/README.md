# Adversarial validation notes

This directory is evaluator-facing and contains no learner solution. Executable adversarial cases live with the sealed reference tests so they cannot leak behavioral edge cases into the public progression.

The current bounded suite probes:

- repeated dynamic parser growth with a 64 KiB quoted word;
- 32 downstream pipeline consumers, which magnifies descriptor/EOF mistakes;
- recovery after 200 consecutive syntax errors;
- monotonic identity and collection across 25 short-lived background jobs.

Important cases still reserved for an independent harness include deterministic allocation and syscall failure injection, low `RLIMIT_NOFILE`/`RLIMIT_NPROC`, initially closed descriptors 0–2, simultaneous stop/continue/exit events, terminal loss, PID reuse, and sanitizer-backed randomized token streams. Those require harness control not assumed in this generated workspace.

No fuzzing or adversarial-validation label is claimed.
