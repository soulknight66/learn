# CS186 Database Systems Kickoff

> Unit: `managed_unit_01_relational_pipeline` · Source class: supplied catalog metadata plus manager-authored material · Validation label: `PREPARED_NOT_LEARNER_VALIDATED`

This study unit is a focused entry point into database internals, not a compressed version of the whole CS186 course. You will build a small relational execution component in Java and use it to practice the habits that turn a correct algorithm into dependable software: explicit contracts, narrow interfaces, lifecycle discipline, reproducible tests, and evidence that another person can verify.

## Where this unit fits

The catalog describes a demanding database-systems course spanning SQL, query execution and optimization, storage, indexes, concurrency, recovery, and NoSQL, with Java projects. This kickoff covers only an in-memory row-at-a-time operator pipeline. It deliberately does not cover parsing, disk storage, joins, optimization, indexes, transactions, recovery, or NoSQL.

The kickoff was written by the course manager from the supplied catalog snapshot. It is not represented as an official UC Berkeley unit or assignment. Catalog links to the course website, recordings, an assignments index, and a candidate repository were not retrieved or verified. You do not need them for this unit.

## What you will learn

By the end of this unit, you should be able to:

- turn relational behavior into contracts that callers and tests can observe;
- organize a small Java subsystem so data, execution, validation, and lifecycle concerns remain separate;
- compose scan, filter, project, and limit behavior without hidden coupling;
- test ordering, boundaries, invalid use, ownership, and early termination deterministically; and
- leave a reproducible build, test, and provenance trail.

## Working assumptions

You should already be comfortable with asymptotic analysis, basic data structures, Java, and automated testing. Relational database experience is helpful but not required: the task defines the model it expects. Use only tools and dependencies already available in your learning environment; the unit has no network dependency.

Plan for about ten focused hours:

1. Read the task and write down the public contracts before coding (1 hour).
2. Implement the typed data model and lifecycle skeleton (2 hours).
3. Implement and compose the four operators (3 hours).
4. Build adversarial, integration, and fixed-seed generated tests (2 hours).
5. Refactor, document decisions, and capture a clean test run (2 hours).

## Completion boundary

Finishing the files or reporting that tests pass does not by itself complete the unit. A controlled evaluator must run the submission and record the result. Even a validated pass completes only this manager-authored kickoff; it is never evidence that you completed CS186 or any other unit in the catalog.
