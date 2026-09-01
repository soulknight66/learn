# Independent review

## Verdict

**REVISE.** The executable reference was consistent with the public contract in the available
builds, submitted suites, manual code review, and an independent 90,000-operation model comparison.
One solution-bearing scheduler explanation is nevertheless inconsistent with the actual API and
state semantics, so the pack should not pass unchanged.

## Prioritized finding

### P1 — Sealed scheduler answers invent a `current` field and teach a false invariant

`sealed/debugging/02-dual-running/ANSWER.md:5-9` says scheduling updates `current` and that there is one
running process exactly when `current` names that slot. `sealed/review_exercises/01-scheduler/ANSWER.md:3-5`
also says blocking or exiting clears `current`.

There is no `current` member in `mica_scheduler_t`; the public member is `cursor`. Per
`REQUIREMENTS.md:29` and `sealed/DESIGN.md:20`, `cursor` is scheduling history: it records the slot
chosen by the last successful scheduling decision. `mica_scheduler_block` and
`mica_scheduler_exit` change only the process record and deliberately leave the cursor intact. An
independent probe observed `selected=1 cursor=0 running=0 selected_state=3` after spawn, schedule,
and block, directly disproving the answer's claimed equivalence.

This matters because a learner consulting the sealed answer could add a forbidden field, reset the
cursor, or write an incorrect invariant test. Revise both answers to distinguish the count of
`RUNNING` records from the persistent round-robin cursor. The correct invariant is at most one
`RUNNING` record; zero may coexist with a cursor that still points to a blocked, exited, reaped, or
reused slot.

## Other review results

- Correctness evidence: the reference suite passed, the public suite passed against the reference,
  and independent long state-machine sequences matched separate scheduler, VM, and RAMFS models.
  No executable contract defect was found in the exercised scope.
- Reproducibility: the documented GCC/Make commands reproduced in a scratch copy. Two clean builds
  produced identical aggregate output hashes, and stricter warning variants compiled cleanly.
- Progressive disclosure: learner-facing requirements, milestones, symptoms, and public tests avoid
  solution code; solution-bearing material is placed under `sealed/`. End-to-end student-view
  filtering was not available to verify.
- License/provenance: catalog CC0 metadata is kept separate from the linked tutorial's
  `NOASSERTION`, and the artifact expressly claims no linked content was copied. The records are
  internally consistent, but the upstream snapshot was unavailable for an external comparison.
  The generated-material statement is not a general redistribution license, so none should be
  inferred.
- Validation honesty: the manifest stays `GENERATED` / `PARTIAL`, requires independent validation,
  and marks `productionized` false. The candidate repeatedly identifies its own test output as local
  evidence and accurately lists the missing production, boot, fuzz, benchmark, and transfer work.

## Disposition

Correct the two scheduler answer files and rerun the documentation/API consistency review. The
executable reference does not need repair based on the checks completed here.
