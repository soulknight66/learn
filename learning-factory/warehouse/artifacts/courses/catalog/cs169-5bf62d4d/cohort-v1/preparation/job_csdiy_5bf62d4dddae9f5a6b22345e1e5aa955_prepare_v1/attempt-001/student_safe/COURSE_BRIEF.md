# UCB CS169 Software Engineering — Kickoff Brief

## What this unit is

This is a six-hour, manager-authored kickoff inspired by the catalog description of UC Berkeley's software-engineering course. It is designed for someone who is already comfortable with algorithms and now wants practice turning correct logic into software that another person can run, test, understand, and change.

You will build one narrow vertical slice: an HTTP service around dependency ordering. The algorithm should be familiar; the challenge is the engineering boundary around it—an explicit contract, predictable failures, tests, reproducible commands, and concise decisions.

This is **not** an official CS169 unit, a substitute for its textbook or assignments, or evidence that you completed the course. Passing it can establish only that you completed this kickoff.

## Outcomes

By the end of the unit, you should be able to:

- turn a user need into acceptance scenarios and a small service contract;
- expose algorithmic behavior through a deterministic HTTP interface;
- separate domain behavior from transport and input-validation concerns;
- test successful, invalid, and failure paths at useful boundaries; and
- leave reproducible evidence that a reviewer can check without relying on your claim.

## Working assumptions

The catalog describes an agile SaaS course using Ruby and JavaScript, with a textbook, course site, recordings, and assignments. In this workspace, only catalog metadata is available. The site and textbook are unverified links, while recordings and assignments have no direct locator. None is required for this unit, and you should not search for restricted course content or solutions.

Use Ruby or JavaScript if practical, with a minimal installed HTTP library or framework. If neither is available, use another language you can run locally and document the reason. The assessed engineering behaviors are language-independent.

## Unit boundary

Budget about six focused hours. Build only the service slice specified in `STUDY_TASK.md`, answer the prompts in `COMPREHENSION.md`, and stop. A user interface, database, authentication, cloud deployment, production scaling, and reconstruction of official CS169 assignments are deliberately outside this kickoff.

Keep secrets, credentials, copied solutions, and private course material out of every submission artifact.
