# Answer: runner safety review

Joining arguments destroys their boundaries and a shell interprets metacharacters, substitutions, and redirections. Pass an immutable argv sequence with `shell=False`. Build a minimal environment from fixed defaults and explicit spec values rather than copying caller state.

An unlimited wait can hang forever, while capture-all can exhaust memory or deadlock if pipes are not drained together. Use a positive timeout, concurrent draining with retention limits, and explicit truncation. Start a new session/process group; on timeout terminate the group, wait for it, and record `FAILED`.

Claim `RUNNING` with an expected-state transaction before launch so only one caller owns the attempt. If launch raises, move `RUNNING -> FAILED`. If a launched payload exits, record `EXITED` plus its exact code—even when nonzero—because that is distinct from harness failure. State and event writes must be atomic.

Tests should use literal metacharacters in argv, a parent-only environment marker, large output on both streams, a sleeping child, a missing executable, a nonzero payload, and concurrent claims. These validate the runner contract but do not exercise user/mount/PID namespaces, rootfs contents, cgroups, capabilities, seccomp, or host policy; they are not isolation evidence.
