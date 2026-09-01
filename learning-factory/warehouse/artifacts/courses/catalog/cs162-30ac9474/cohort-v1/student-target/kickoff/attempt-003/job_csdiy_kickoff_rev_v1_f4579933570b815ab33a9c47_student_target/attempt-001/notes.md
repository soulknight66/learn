# Unit 1 revision notes

## Scope

I revised only the self-contained deterministic round-robin simulator kickoff. This submission does not claim completion of CS162, later units, course credit, acceptance by the evaluator, or transfer verification. LEARNER_MATERIAL, PRIOR_ATTEMPT, and EXAMINER_FEEDBACK were used as read-only inputs.

## What changed

The examiner could not reproduce the prior prose because its named source, build, tests, and engineering records were absent. I addressed that artifact-integrity problem by creating the actual implementation and support files in this workspace:

- five separated C17 modules plus headers and the shared Task model;
- a Makefile with build, unattended test, and clean targets;
- a 22-test black-box suite with exact output and failure-atomicity oracles;
- DESIGN.md, TESTS.md, RESPONSES.md, and EVIDENCE.txt;
- MANIFEST.txt, which names every intended submitted file, including these new learner records.

The implementation validates the whole workload before scheduling or emitting normal output. It stores input order independently from stable arrival order, uses a bounded circular FIFO, admits arrivals through each slice endpoint before requeueing, jumps over idle intervals, and reports results in original input order.

## Concrete observations

- A clean default build under GCC 8.5.0 with C17, Wall, Wextra, and Wpedantic exited 0 and emitted no compiler diagnostics.
- The final in-workspace make test run exited 0: 22 named tests passed in 0.850 seconds. One test also compared 40 seeded workloads with an independent event model.
- The two-task endpoint discriminator, A 0 2 and B 1 1 at quantum 1, produced B first-run 1/completion 2 and A completion 3. This observes endpoint admission before requeue.
- A valid task followed by Bad 2x 1 returned nonzero with zero stdout in test_late_malformed_line_emits_no_partial_output.
- Exact-limit workloads of 128 tasks and 10,000,000 total service passed; one-above cap cases failed with zero stdout.
- A build with the additional Wconversion and Wshadow diagnostics exited 0 without diagnostics, and the suite passed against that binary.
- ASan/UBSan instrumentation compiled, but the host linker lacked libasan.so.5.0.0 and libubsan.so.1.0.0. Therefore no dynamic memory-safety run is claimed; EVIDENCE.txt labels it NOT RUN.

## Retained lesson

Prose inventories and reported commands are not substitutes for submitted artifacts. This revision pairs every claim with a present file or a reproducible command, and leaves final acceptance to the independent evaluator.
