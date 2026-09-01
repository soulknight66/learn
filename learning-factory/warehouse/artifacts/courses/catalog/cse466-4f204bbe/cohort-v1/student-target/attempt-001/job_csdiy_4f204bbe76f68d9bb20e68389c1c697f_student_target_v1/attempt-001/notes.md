# Learning notes: Linux process boundaries kickoff

## Scope and sources

I read only `COURSE_BRIEF.md`, `STUDY_TASK.md`, and `COMPREHENSION.md`. I attempted
the bounded, manager-authored kickoff: one harmless local Linux command runner,
its fixtures, tests, evidence, and written responses. This work is not an
official ASU or pwn.college module and says nothing about completion of CSE466
or its catalog challenges.

## Initial hypotheses and experiments

1. **An argument vector is a safer and more exact interface than a command
   string.** I passed empty text, spaces, `*`, `;`, quote characters, and a dollar
   expression through `Popen` with `shell=False`. The JSON-emitting fixture
   received the same list element-for-element. This tests preservation instead
   of merely searching source for the absence of a shell call.

2. **A retention bound alone will not keep execution live.** The flood fixture
   writes 262,144 bytes concurrently to each stream. The selector loop observed
   every byte while retaining 1,024 bytes from each. Finishing this test shows
   why excess bytes must still be drained: discarding affects memory, whereas
   reading affects pipe backpressure.

3. **One process group is the appropriate cleanup unit for this lab.** A new
   session isolates the child tree from the runner. Tests recorded both parent
   and descendant PIDs. The cooperative tree disappeared after `SIGTERM`; the
   tree that ignored `SIGTERM` disappeared after the 0.25-second grace deadline
   and escalation. Both tests checked PIDs after return rather than trusting the
   report alone.

4. **Timeout must be an outcome decision, not an interpretation of the final
   negative return code.** The implementation makes timeout activation sticky.
   A run completed before the deadline is classified by its return status; a run
   incomplete at the deadline stays `timed_out` even though cleanup later causes
   a signal return. Repeated near-boundary tests accept either timing result but
   reject contradictory report fields.

5. **Atomic report naming needs a same-directory temporary.** The report is
   fully serialized, written, flushed, and `fsync`ed before `os.replace`. This
   protects the destination name from partial JSON. It does not turn disk,
   permission, or isolation failures into successes.

## Working model

The supervisor has a small state machine: configuration, spawn, running,
cooperative termination, forced termination, and one terminal report outcome.
The crucial stream invariant is:

```text
0 <= bytes_stored == decoded Base64 length
   <= min(configured limit, bytes_observed)
truncated == (bytes_observed > bytes_stored)
```

The OS supplies facts the model depends on: `start_new_session` creates a group
that `killpg` can address; pipe readiness does not imply EOF; child termination
must still be reaped; wall time can jump, so deadlines require a monotonic clock;
and process exit can race with the observer reaching its deadline.

## Production-engineering lessons

- Runtime identity is part of reproducibility. The default `python3` was 3.6,
  while the recorded implementation run used the provided Python 3.11.5.
- An outer test deadline must include interpreter startup and scheduling delay.
  My first 50 ms boundary test could terminate before its PID fixture initialized.
- Independent evidence is stronger than a success claim: exact argv comparison,
  decoded-byte checks, observed byte totals, recorded PIDs, and full test output
  each validate a different behavior.
- Bounds need both a safety statement and a progress argument. The array remains
  small only because appends are capped; the process remains live only because
  both pipes continue to be serviced.
- Cleanup policy is not sandboxing. A deliberate session escape, filesystem or
  network access, user separation, and CPU/memory accounting remain outside this
  first unit.

## Boundary reached

The listed kickoff deliverables pass the local clean-directory suite. I stopped
at that boundary and did not attempt catalog challenges, external targets,
privileged behavior, or later course material.
