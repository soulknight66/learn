# Review: the child boundary

Assume the interactive parent ignores `SIGINT`, `SIGTSTP`, and `SIGTTOU`. It calls `launch_candidate` once per simple external command and later waits for `pid`.

Review `candidate.c` without running it first. Find at least five issues. For each:

- identify the violated requirement or invariant;
- describe a concrete input, signal, or scheduling order that exposes it;
- state whether the repair belongs in the parent, child, or both;
- propose a bounded regression test.

Pay special attention to what is safe after `fork`, what state survives `exec`, and which PID/process group receives terminal-generated signals.
