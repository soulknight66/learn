# Independent review

Verdict: **REVISE**

The pack is unusually clear, honest about its validation state, and mostly reproducible. The starter, reference, public suite, sealed suite, documentation, and exercises form a useful learning progression. One independently reproduced descriptor bug in the sealed reference prevents a pass, because the reference fails an otherwise valid instance of the stated redirection contract.

## Prioritized findings

### P1 — Redirection closes the destination descriptor when open returns fd 0 or 1

CANDIDATE/sealed/reference/src/execute.c:50-71 always calls dup2 and then closes the descriptor returned by open. If inherited standard output is closed, open for an output redirection can return fd 1. In that case dup2(1, 1) is a successful no-op and the following close disables the command's redirected output.

The reviewer reproduced this through the normal minish executable:

~~~text
closed-stdout redirection: exit=1, size=0,
stderr='/usr/bin/printf: write error: Bad file descriptor\n'
~~~

This conflicts with CANDIDATE/REQUIREMENTS.md:37-38. The same aliasing hazard exists around pipeline duplication and closure at execute.c:85-93, and the analogous fd 0 case can affect direct executor use with input redirection. The sealed tests always supply open standard descriptors, so they do not expose it.

Revise the descriptor-moving logic to account for oldfd equal to the target fd, and add deterministic tests with fd 0 and fd 1 initially closed. The submitted candidate was not modified.

### P2 — Retrying close after EINTR is not a portable safe-close operation

CANDIDATE/sealed/reference/src/execute.c:11-21 retries close on EINTR. On systems where the first close has already released the descriptor, a retry can act on a reused descriptor. Focused GCC 15.2.0 analysis reported analyzer-fd-double-close and exited 1.

No runtime reuse was reproduced in this single-threaded shell, so this is a portability and teaching risk rather than a second observed failure. A reference implementation should not present unconditional close retry as the ownership pattern.

### P3 — Starter error paths do not demonstrate unconditional cleanup

CANDIDATE/starter/src/main.c:40-49 continues after lexer failure without calling token_list_free and after parser failure without calling pipeline_free. The bundled reference implementations self-clean and zero their outputs, so the reviewed reference does not leak on these paths. However, the contract says failed outputs remain safe to free, and a learner may reasonably retain a partially allocated, destructible result.

Calling both destructors on all exit paths would make the ownership lesson explicit and keep the loop correct for every implementation allowed by that wording.

## What held up

- The configured GCC 15.2.0 build works with C17, POSIX feature selection, strict warnings, and errors-on-warning.
- The untouched starter compiles and fails its sample suite as documented; no solution is embedded in it.
- The reference passed the public suite and the sealed unit, CLI, low-fd-pressure, process-group, and PTY checks.
- Twelve separate reviewer-authored black-box assertions passed, including exact line limits, signal-status mapping, last-stage status, redirection precedence, append, cd via HOME, exit-with-last-status, comment boundaries, recovery, and noninteractive prompt suppression.
- ASan and UBSan emitted no diagnostic in the bounded sealed unit run with leak detection disabled.
- Learner-facing areas contain no reference, answer, or nested sealed file. Solution-bearing material is confined to the root sealed tree, subject to the factory's external view filtering.
- Requirements, concepts, design questions, and exercises explain ownership and process mechanics well. Public-test limitations are explicit.
- Manifest and prose consistently retain GENERATED/PARTIAL, require independent validation, deny productionization, and make no fuzz or benchmark claim.
- The provenance document consistently separates the CC0 catalog record from the NOASSERTION linked resource.

## Residual limits

The upstream source and authorship/non-copy claim were not independently available for comparison. LeakSanitizer could not run under ptrace. No fuzzing, benchmark, coverage target, fault-injection campaign, broad PTY matrix, or publication-view test was available. Builder-owned scripts and this advisory review do not publish REVIEWED or any other validation label.
