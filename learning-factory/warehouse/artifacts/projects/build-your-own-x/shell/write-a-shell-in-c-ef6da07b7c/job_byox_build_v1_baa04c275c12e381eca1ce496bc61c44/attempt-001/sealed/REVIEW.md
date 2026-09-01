# Reference implementation review

## Summary

The reference is suitable as a bounded pedagogical oracle for the declared grammar. Strict-warning builds and the local suites cover token ownership, malformed grammar, concurrent pipelines, status normalization, builtins, retained jobs, process-group membership, and one pseudo-terminal interrupt path.

It is not production-ready. The most important gaps are lifecycle and event-loop behavior rather than the happy-path process graph.

## Findings

1. **High — active background jobs are not shut down or detached deliberately.** On shell exit, job metadata is freed and children are inherited by the environment's subreaper/init. A production policy must choose to wait, warn, disown, or send bounded `SIGHUP`/`SIGTERM` escalation and then prove reaping behavior.
2. **High — completed job retention is unbounded.** Jobs remain until `wait`. An interactive session can exhaust memory by starting many fast jobs without waiting.
3. **Medium — no asynchronous child notification.** A dead background child can remain a zombie while the shell blocks in `getline`. Collection happens at the next command boundary. A self-pipe plus `pselect`/event loop is the conventional portable direction.
4. **Medium — process-group setup failure is diagnosed but not made transactional.** The parent continues after unexpected `setpgid` failure. A hardened implementation should terminate and reap the entire partially launched pipeline because signal routing can no longer be trusted.
5. **Medium — stopped-job usability is incomplete.** State is retained, but `fg`, `bg`, targeted `wait`, and continued-state commands are out of scope. A stopped job can occupy resources until an external actor changes it or the shell exits.
6. **Medium — interactive coverage is narrow.** The PTY test checks Ctrl-C recovery for a single foreground command. It does not yet cover Ctrl-Z across a multi-process pipeline, terminal mode restoration, nested sessions, orphaned process groups, or a terminal disappearing.
7. **Low — deep pipelines allocate all descriptors up front.** Correct for ordinary depth, but a rolling descriptor strategy would tolerate larger pipelines under the same `RLIMIT_NOFILE`.
8. **Low — diagnostics are stable only by prefix and meaning.** They are not localized or assigned machine-readable codes. This is acceptable for the contract but weak for tooling.

## Positive evidence

- Parsing is completed before launch, and error outputs are empty pipeline objects.
- The large producer/consumer test would deadlock if execution were serialized or a parent write end remained open.
- A dedicated helper observes that both stages share the first child's process group.
- The exec error is saved before diagnostic formatting, preserving the 126/127 distinction.
- Foreground terminal transfer is exercised in a real pseudo-terminal, not inferred from batch mode.

No `REVIEWED` label is claimed; only an independent validator can assign it.
