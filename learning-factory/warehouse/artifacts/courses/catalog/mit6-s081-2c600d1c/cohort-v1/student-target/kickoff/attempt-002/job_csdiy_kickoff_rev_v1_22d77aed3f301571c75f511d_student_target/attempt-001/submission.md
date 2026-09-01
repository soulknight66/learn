# Revised Submission — unit_kickoff_vmwalk_v1

## Status

**REVISION SELF-CHECKED / CONTROLLED VALIDATION PENDING.** This is a bounded
kickoff resubmission, not a claim of kickoff completion, MIT 6.S081
completion, xv6 work, or transfer verification. Only the worker harness may
apply HARNESS-VALIDATED.

## What changed

The earlier evaluated package omitted every implementation artifact it
described. This revision supplies:

- Makefile and the src/main.c, src/vmwalk.c, and src/vmwalk.h C11 modules;
- deterministic behavioral tests and checked-in fixtures under tests/;
- DESIGN.md and all eight answers in COMPREHENSION_RESPONSES.md;
- build/test logs, source inventory hashes, and evidence/SELF_CHECK.md; and
- fresh notes.md, submission.md, and debugging-log.md matching this revision's
  observed state.

The implementation validates the complete trace before emitting access
results, enforces all declared capacities, preserves modeled-fault semantics,
and separates status 0, 1, and 2 outcomes.

## Reproduction

From the submission root, run:

    make clean all
    make check

The exact learner-run output, versions, and statuses are recorded under
evidence/. Those records are reproducibility evidence only. The independent
controlled fixture suite was not available as learner material and is neither
inferred nor claimed to have run.
