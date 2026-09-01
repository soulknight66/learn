# Study Task: Dependency-Planner Service

## Timebox and purpose

Spend at most six focused hours building a small HTTP service that turns tasks and dependency pairs into a valid execution order. Because topological ordering should already be familiar, put most of your attention on contract design, test boundaries, failure behavior, and reproducibility.

The fictional user story is:

> As a release engineer, I want to submit a set of jobs and precedence constraints so that I receive a repeatable safe execution order or a useful explanation that no order can be produced.

Before implementation, restate this story in your own words and write acceptance scenarios in `engineering-notes.md`.

## Required service contract

Implement a service with these endpoints:

### `POST /plans`

Accept JSON with:

- `tasks`: an array of unique, non-empty strings;
- `dependencies`: an array of two-string pairs `[before, after]`; and
- every name in a dependency present in `tasks`.

For a valid acyclic request, return HTTP 200 and JSON containing `order`. The order must contain every task exactly once and respect every dependency. When more than one task is eligible, choose the lexicographically smallest task so identical requests produce identical results.

For a syntactically valid request whose dependencies contain a cycle, return HTTP 422 and a JSON error object with the stable machine-readable code `cycle_detected`. Do not return a partial plan as if it were usable.

For malformed JSON or a request that violates the input rules, return HTTP 400 and a JSON error object with a stable machine-readable code. Include a useful human-readable message, but do not expose a stack trace.

### `GET /health`

Return HTTP 200 and a small JSON response indicating that the process can handle requests. This is a liveness check, not proof that every dependency is healthy.

## Engineering work

1. Write the user story, acceptance scenarios, and a short contract sketch before implementation.
2. Create at least one failing automated test for a required behavior, record that red state briefly, and then implement the smallest change that makes it pass.
3. Keep dependency planning separable from HTTP parsing and response construction.
4. Add automated tests for a normal chain, independent tasks and deterministic tie-breaking, a cycle, an unknown task in a dependency, duplicate task names, and malformed input. Include at least one endpoint-level test.
5. Provide one command to start the service and one command to run all tests from a clean checkout. Use bounded local dependencies; do not require credentials or a paid service.
6. Run the complete test suite and save the command and output in `evidence/test-output.txt`. Remove secrets, machine-specific tokens, and irrelevant logs.
7. Finish the short decision and reflection entries described below, then answer `COMPREHENSION.md` in `responses.md`.

## Submission artifacts

Submit:

- application source and dependency/lock files;
- automated tests;
- `README.md` with prerequisites, setup, start, test, example request, contract summary, and known limitations;
- `engineering-notes.md` with the story, acceptance scenarios, initial failing-test note, one design decision and rejected alternative, and a short iteration reflection;
- `evidence/test-output.txt` from the full test command; and
- `responses.md` containing your numbered answers to the comprehension prompts.

Choose a simple layout and name it in the README. A reviewer should not have to infer commands or search for the service entry point.

## Suggested time allocation

- 45 minutes: contract and acceptance scenarios
- 2 hours: first endpoint-level slice and core planner
- 90 minutes: validation, failure paths, and tests
- 60 minutes: reproducibility, documentation, and evidence
- 45 minutes: comprehension responses and final review

Stop after the required slice. Do not add a UI, persistence, authentication, deployment, parallel scheduling, task durations, or package-management features. List a tempting extension as deferred work instead of implementing it.

## Completion check

Before submission, confirm that another person can use only your README to run the tests and service, the evidence file comes from the submitted version, each required behavior has executable coverage, and your notes describe what actually happened. These checks concern only this kickoff unit and make no claim about completing CS169.
