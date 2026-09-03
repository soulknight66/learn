# Independent review

Verdict: **REVISE**

Builder job: job_byox_build_s2_d6d8903610981a8e77f457c74e3f305d  
Project: project_88e5a9a922f8f9e2166223c1333f28f9

The pack is unusually clear and candid: its normal and sanitizer results reproduce, its labels remain conservative, and its learner/reference separation is clean at the directory level. It is not ready for an advisory pass because independent probes found observable reference defects and an unsafe failure path in the PTY validator.

## Prioritized findings

### 1. High — the lexer violates its explicit byte grammar

REQUIREMENTS.md says only unquoted space and tab separate tokens. At CANDIDATE/sealed/reference/src/msh.c:173, the reference also treats carriage return and newline as separators.

An independent invocation with an unquoted argument containing carriage return, equivalent to the byte string a\\rb, returned status 0 and wrote:

~~~text
<a>
<b>
~~~

The stated grammar requires one argument and the byte sequence represented by <a\\rb>. This matters for CR bytes in input, including CRLF-framed batch data. Restrict lexical separators to space and tab, decide explicitly how embedded line terminators passed through -c are handled, and add byte-oriented regression cases.

### 2. High — child redirection closes its own standard descriptor

At CANDIDATE/sealed/reference/src/msh.c:778-794, each successful dup2 is followed by an unconditional close of the opened descriptor. If fd 0 was closed before launch, open for input may return 0; dup2(0, 0) does nothing and close(0) then invalidates the required input. The analogous failure occurs for output when fd 1 was closed.

Observed independently:

~~~text
CLOSED_STDIN_REDIR  1  stdout=''  EBADF=True
CLOSED_STDOUT_REDIR 1  file=''    EBADF=True
~~~

Only close the source when it differs from the destination. Audit the pipe setup for the same descriptor-aliasing class, or normalize all internal descriptors above the standard range. Add tests that launch the shell with fd 0 and fd 1 closed.

### 3. High — inherited SIGCHLD=SIG_IGN corrupts foreground status

initialize_shell does not restore SIGCHLD to its required waitable disposition. POSIX preserves an ignored disposition across exec, so children can be auto-reaped. wait_for_foreground then encounters ECHILD, leaves the process record at its zero-initialized status, frees the still-not-Done job, and reports success.

With SIGCHLD ignored before exec, /bin/sh -c 'exit 7' produced shell status 0. Normalize SIGCHLD during initialization and treat an unexpected ECHILD as an execution failure rather than a valid stored status. Add a deterministic inherited-disposition test.

### 4. Medium — the PTY validator is not bounded on failure

CANDIDATE/sealed/reference_tests/test_reference.py:169 and :178 call waitpid(child, 0) without a deadline. If a target prints prompts but ignores exit, the one-second read deadline expires and the exception path blocks indefinitely. The final cleanup at :183 kills only the shell PID, not the process group it created, so a foreground or background descendant can escape.

This conflicts with CANDIDATE/AGENTS.md, which requires bounded tests and cleanup of created process groups. Use a deadline-driven WNOHANG loop followed by TERM/KILL escalation, and clean up the session or process group.

### 5. Medium — provenance is internally consistent but not tamper-evident

The manifest field named provenance_sha256 contains 5cf87366..., which matches PROVENANCE.json's self-declared snapshot_sha256. The actual SHA-256 of CANDIDATE/PROVENANCE.json is 8aa702b8b64241bda70f3a63e3d1b9a681e7dc87f4d5930b9b4f764f584e5dad. environment/audit.py checks only that the two embedded values agree.

If the field is intentionally a source-snapshot identifier, document that semantics and add a separately named digest binding the provenance document. If it is intended to bind PROVENANCE.json, generate and verify the actual file digest. The immutable source snapshot was unavailable here, so the other declared hashes remain unverified.

### 6. Medium — public feedback does not cover the hardest milestone

The nine public tests cover useful M0-M4 behavior, but there is no positive public case for background pipelines, job IDs/state, fg, stop/resume, or terminal handoff. exit behavior is also only in the sealed suite. This weakens the README claim that individual tests turn green across the listed milestones and leaves learners without feedback for M5.

Expose bounded black-box cases for basic background/jobs/fg behavior and a robust optional PTY smoke test without revealing reference internals.

### 7. Low — numeric operand parsing is looser than the documented syntax

strtol accepts leading whitespace and signs. The reference accepted the quoted operand ' 7' as a valid exit status and terminated with 7; it also accepts -0. Require the complete operand to match the intended decimal grammar before conversion. Apply the same lexical check to fg job IDs.

## Confirmed strengths

- GCC 15.2.0 normal builds were warning-clean, and GCC -fanalyzer reported no issue.
- Reference suites reproduced at 9/9 public, 12/12 sealed, and 4/4 adversarial.
- ASan and UBSan reproduced those passes; the LeakSanitizer blocker was accurately disclosed.
- An additional 25-case black-box matrix passed in ordinary launch conditions.
- Syntax is parsed before execution, long pipelines reached EOF, status mapping and process grouping worked, and parent/child built-in contexts behaved as documented.
- The manifest does not overclaim BUILDS, TESTED, FUZZED, BENCHMARKED, REVIEWED, TRANSFER_VERIFIED, or PRODUCTIONIZED.
- Learner-facing roots contained no discovered reference source or answer-key leak. The license boundary candidly records the linked tutorial as NOASSERTION and says it was not copied.

## Recommendation

Fix findings 1-4 and add regressions before requesting another independent review. Clarify the provenance digest semantics and improve public M5 feedback in the same revision. A later PASS would remain advisory; only orchestrator-captured validation may publish REVIEWED.
