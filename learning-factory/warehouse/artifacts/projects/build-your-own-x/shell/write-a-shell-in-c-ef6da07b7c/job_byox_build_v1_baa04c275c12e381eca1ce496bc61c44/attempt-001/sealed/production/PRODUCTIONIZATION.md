# Productionization assessment

`productionized: false` is intentional. The implementation demonstrates the requested concepts but is not a security boundary or a general command-language runtime.

Before production use, at minimum:

- define a background-job shutdown, detach, and reaping policy with bounded escalation;
- replace command-boundary child polling with a signal-aware input/event loop;
- add `fg`, `bg`, targeted `wait`, terminal-mode save/restore, and complete stopped/continued transitions;
- make unexpected `setpgid` and `tcsetpgrp` failures transactional;
- cap or prune retained jobs and bound input, pipeline depth, and allocation totals;
- use a rolling-pipe algorithm or enforce a depth limit below `RLIMIT_NOFILE`;
- add fault-injection wrappers for allocation, pipe, fork, setpgid, dup2, exec, wait, and terminal calls;
- test on Linux, macOS, and BSD-like PTY implementations under sanitizers and leak checkers;
- specify locale, byte/NUL handling, diagnostic stability, and behavior when standard descriptors begin closed;
- add an explicit threat model. This parser does not quote or sandbox arbitrary untrusted command text.

Operational readiness would also require structured observability, resource limits, dependency/toolchain pinning, reproducible builds, release signing, and an incident response owner. No benchmark, fuzzing, transfer, review, or production label is asserted by this generated pack.

The sealed reference remains an educational oracle whose known gaps are documented in `sealed/REVIEW.md`.
