# UCB CS126: Probability Theory — Kickoff Brief

## What this workspace covers

This is a bounded, course-manager-authored first study unit for the cataloged course **UCB CS126: Probability theory**. It is a bridge from algorithms knowledge to probability-aware software engineering. It is not represented as an official Berkeley unit, and finishing it does not mean that you have finished the course.

The full catalog entry estimates about 100 hours and names CS70, calculus, and linear algebra as prerequisites. This kickoff is designed for roughly **8 hours**. It assumes you are comfortable with finite sums and products, asymptotic reasoning, basic probability, Python, and unit tests.

## First-unit focus

You will turn a collision-probability model into a small, reproducible Python component. The mathematical object is deliberately compact so you can concentrate on the engineering boundary between a model, a simulation, tests, a command-line interface, and an experiment record.

By the end of the unit, you should be able to:

- state the sample space and assumptions behind a collision model;
- distinguish an exact calculation from a Monte Carlo estimate;
- make randomized code reproducible without coupling every caller to global state;
- test deterministic properties of probabilistic software and justify any statistical check;
- emit enough structured evidence for another developer to repeat an experiment; and
- explain numerical and modeling limitations rather than hiding them.

## Materials and boundaries

Everything required for this kickoff is local:

1. `COURSE_BRIEF.md` — orientation and scope;
2. `STUDY_TASK.md` — the project specification; and
3. `COMPREHENSION.md` — questions to answer in your submission.

The catalog also points to a Fall 2020 course site, a Springer textbook in several formats, a Jupyter Book, and a GitHub repository. Those links were **not retrieved or verified** for this unit and are optional context, not prerequisites. The catalog mentions assignments and nine labs but does not contain their files or a verified official sequence. Do not claim to have completed them.

## Working expectations

Use Python 3 and keep the required implementation within the standard library. Favor a small, inspectable design over a framework. Run experiments only after deterministic tests pass, retain the parameters used to produce every reported observation, and distinguish observations from conclusions in your report.

Your submission is evaluated from its artifacts and validation results, not from a statement that it works. Follow `STUDY_TASK.md` for the required artifact layout. Complete the questions in `COMPREHENSION.md` independently; that document intentionally contains no solutions.
