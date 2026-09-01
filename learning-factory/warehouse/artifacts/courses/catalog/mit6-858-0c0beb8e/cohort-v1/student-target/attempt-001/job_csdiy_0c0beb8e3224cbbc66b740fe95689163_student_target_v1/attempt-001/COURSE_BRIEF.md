# MIT 6.858 Catalog Kickoff: Systems-Security Engineering

## Status and scope

This packet prepares one manager-authored kickoff unit aligned with the catalog description of **MIT 6.858: Computer System Security**. It is not an MIT lecture or lab, does not reproduce unavailable MIT material, and is not evidence that you have completed any part of the official course.

The unit is **Threat Models and a Tested Authorization Boundary**. Plan for about 8 hours, with a hard stop at 10 hours. Completing it can establish evidence for this unit only. It cannot establish whole-course completion, transfer of learning, or completion of any official lab.

## Why this unit

Algorithmic strength helps with exhaustive case analysis and invariants. Real security engineering adds different pressures: requirements are incomplete, inputs cross trust boundaries, failure behavior matters, and a claim is useful only when another person can reproduce the evidence.

You will build a small local authorization component. The code is deliberately modest so that most of the work can go into:

- defining what is trusted and why;
- converting prose into a precise, fail-closed contract;
- separating parsing from policy;
- testing invariants as well as examples;
- keeping a useful debugging record; and
- stating limitations without disguising them as completed work.

## Unit outcomes

By the end of this kickoff, you should be able to:

1. describe assets, actors, trust boundaries, assumptions, abuse cases, and non-goals;
2. implement deterministic authorization decisions for a finite policy;
3. reject malformed or ambiguous input before it reaches the policy core;
4. derive a systematic test space from roles, actions, ownership, and tenancy;
5. run and report reproducible checks; and
6. distinguish a passing local exercise from a production-security or course-completion claim.

## Prerequisites and environment

You need Python 3, the standard library, a text editor, and a local shell. No network access, third-party package, external service, real credential, or course download is required. Comfort with Python functions, data types, and `unittest` is assumed.

Work only with invented local identifiers and test data. Do not probe a real service, reuse real secrets, fetch restricted content, or attempt to locate examiner material. This is a defensive design and testing exercise, not an exploitation task.

## Available and unavailable source material

The supplied source is a CSDIY catalog snapshot. It describes broad course topics, four labs, a final project, a course URL, and a paper URL. The linked pages and paper were not fetched. Official lab specifications, starter code, lecture notes, tests, and the final-project specification are not present. The catalog also records no textbook.

The three files in this packet are self-contained and newly authored for the kickoff. Treat any course title or lab name as provenance context, not as a claim that the corresponding official material is available.

## Suggested working rhythm

- First, write the initial threat model and a decision table before implementing the policy.
- Build a small deterministic core, then put the untrusted-input adapter around it.
- Turn the decision table into tests and add invariant checks that range over the full finite policy space.
- Exercise malformed inputs at the process boundary.
- Keep `debugging-log.md` as you work; record observations, not a reconstructed success story.
- At the timebox, submit the evidence you have and label unfinished work or uncertain claims explicitly.

The detailed contract and deliverables are in `STUDY_TASK.md`. The prompts in `COMPREHENSION.md` are questions to answer in your own words; no answer key is included in the learner packet.
