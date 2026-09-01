# CS189 kickoff: engineering a reproducible classifier

This is a bounded, manager-authored first study unit associated with the catalog entry **CS189: Introduction to Machine Learning**. It is designed for a learner who is already comfortable with algorithms and now wants practice turning mathematical ideas into reliable software.

The supplied catalog describes a UC Berkeley course, names CS188 and CS70 as prerequisites, identifies Python as the programming language, and links a course site and recording playlist. Those external resources were not retrieved. This unit is therefore self-contained; it is not an official UC Berkeley assignment and does not claim to reproduce the CS189 syllabus.

## Unit focus

You will build an exact k-nearest-neighbors classifier and a deterministic experiment around it. The algorithm is intentionally familiar. The harder work is making every behavior explicit: ownership of fitted state, malformed-input handling, tie resolution, train-only preprocessing, model selection, test isolation, repeatable output, and useful automated tests.

By the end of the unit, you should be able to:

- turn a compact mathematical rule into a precise API contract;
- identify and prevent preprocessing and model-selection leakage;
- make randomized data generation and evaluation reproducible;
- test edge cases and state behavior, not just a happy-path accuracy number;
- connect asymptotic analysis to concrete implementation choices; and
- record enough provenance for another engineer to reproduce an experiment.

## Scope and time box

Budget about **8 focused hours**. Use Python 3.11 and its standard library only. The task supplies a deterministic synthetic-data specification, so network access and external course materials are neither needed nor expected.

Read `STUDY_TASK.md` for the build contract and `COMPREHENSION.md` for the written prompts. Keep all requested work under `submission/` as described in the task.

## Evidence boundary

Completion is decided from the submitted code, executable tests, machine-readable experiment record, and written reasoning—not from a claim that the work ran successfully. An independent validator may exercise additional inputs.

Passing this unit, if independently validated, establishes only that this kickoff was completed. It is not evidence of completing CS189, covering its lectures or assignments, or earning UC Berkeley credit.
