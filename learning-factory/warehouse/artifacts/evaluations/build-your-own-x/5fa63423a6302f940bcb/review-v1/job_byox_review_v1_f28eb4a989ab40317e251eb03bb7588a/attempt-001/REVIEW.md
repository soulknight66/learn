# Independent review

Verdict: **REVISE**. The pack is unusually careful about scope and claim hygiene, and most supplied
checks reproduce. Two contract-level defects in the sealed reference remain, so passing the submitted
suite is not enough to promote the artifact beyond its current `GENERATED`/`PARTIAL` posture.

## Prioritized findings

### High — background children become zombies during a foreground wait

`REQUIREMENTS.md:143-144` requires the shell to observe and reap all children and says completed
background processes must not remain zombies. In `sealed/reference/jobs.c:588-601`, the foreground
loop calls `waitpid(-job->pgid, ...)`. A `SIGCHLD` from another job merely interrupts and restarts that
same group-specific wait. The general `waitpid(-1, ..., WNOHANG ...)` sweep does not occur until
`shell_reap_jobs` at line 618, after the foreground job stops or exits.

An independent probe launched `true &` followed by a two-second foreground `sleep`. SID/PPID-scoped
`ps` showed both:

```text
Z    true <defunct>
S    sleep
```

The `Done` notice appeared only after the foreground sleep completed. A long foreground job, or many
quick background jobs, can therefore retain zombies and exhaust process-table resources. The wait
path needs to drain all available child statuses when other `SIGCHLD` events arrive while preserving
the selected foreground job's aggregate state. Add a bounded regression that synchronizes on a quick
background exit while a gated foreground fixture remains alive and asserts that no child is `Z`.

### High — `execvp` silently delegates ENOEXEC files to a host shell

`REQUIREMENTS.md:22` says a pre-existing shell must not interpret command text. The external-command
path at `sealed/reference/jobs.c:735` uses `execvp`. On this glibc host, its specified ENOEXEC fallback
invoked `/bin/sh` for an executable text file with no shebang. The independent fixture contained only
`printf 'HOST_SHELL_FALLBACK\n'`; running that path through `byosh -c` returned 0 and printed
`HOST_SHELL_FALLBACK`.

This crosses the documented language boundary and can execute host-shell syntax that `byosh` itself
does not support. Either explicitly permit and document ENOEXEC fallback, or implement PATH search
with a non-fallback execution primitive and report the failure (normally status 126). The acceptance
suite needs this case.

### Medium — the sealed/student boundary is organized but not transfer-verified

The learner-facing files do not directly link to reference internals, and all answers are under named
`sealed` paths. That is good source organization. It is not an access boundary by itself: the submitted
root contains 23 readable reference, private-test, production-note, and answer files. No generated
student-view tree, explicit allowlist, or harness-owned transfer check was supplied for independent
inspection.

Do not hand the complete `CANDIDATE` tree to a learner or claim `TRANSFER_VERIFIED`. The control plane
should deterministically materialize and validate a learner view that excludes top-level `sealed/`,
nested exercise `sealed/` directories, and private tests. The candidate-authored audit's exclusion of
those paths from a content scan is not evidence that a separate view was actually produced.

### Medium — parser checks impede the modular design the scaffold recommends

`starter/README.md:44-46` allows learners to add internal source files, and lines 63-65 tell them to add
build dependencies. However, `public_tests/Makefile:19-23` compiles each parser test directly with only
`../starter/src/parser.c`. Moving lexing or parser helpers into another translation unit—a design the
teaching material encourages—causes unresolved references even when the learner's own Makefile is
correct.

Expose a stable parser test library/target, or make the test source list configurable through the
starter build. The public parser suite should also exercise its documented command/argument capacity
boundaries; currently those cases exist only as prose guidance.

## Evidence that reproduced

- The starter and sealed reference built cleanly under GCC 8.5.0 with their strict warning flags.
- The starter baseline passed. Its later parser check failed with exactly 17 assertions, matching the
  documented initial learning boundary.
- The sealed suite ran 32 tests with no skips and passed; the public CLI smoke suite also passed.
- All three debugging programs and all three code-review excerpts compiled with the recorded flags.
- The pack audit passed from the clean copy, ten independently enumerated local Markdown links
  resolved, and provenance JSON had the embedded canonical digest.
- The benchmark runner completed a bounded one-iteration smoke run and labeled its output
  `unvalidated local measurement`; this is not benchmark evidence.
- The manifest and prose consistently disclaim independent validation, fuzzing, benchmarking,
  production readiness, and stronger labels. The sanitizer-link failure recorded by the builder was
  independently reproduced.

## License and provenance

The boundary is stated conservatively: catalog metadata is identified as CC0-1.0, the linked tutorial
is `NOASSERTION`, and generated material is not presented as upstream-licensed content. No obvious
upstream names or copied-attribution fragments appeared outside the provenance/boundary metadata.
The upstream checkout was not readable in this review workspace, however, so authorship similarity,
the source commit, and the linked license cannot be independently authenticated here. Also,
“personal educational use” is a purpose statement rather than a reusable distribution license; add an
explicit license if this pack will be redistributed.

## Validation posture

Keep `GENERATED` and `PARTIAL`. The passing submitted suite establishes useful local evidence, but its
coverage missed both independently reproduced defects above. No basis was found for `FUZZED`,
`BENCHMARKED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`, and sanitizer, fault-injection, portability,
and upstream-comparison checks remain incomplete.
