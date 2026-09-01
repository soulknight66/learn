# Course kickoff brief

## Course context

This packet begins a study path associated with **UMich EECS 498-007 / 598-005: Deep Learning for Computer Vision**. It is a bounded, course-manager-authored kickoff for a learner who already has strong algorithms foundations and wants to practice building dependable software.

The kickoff is not an official UMich unit, is not a reproduction of an official assignment, and is not evidence that the wider course has been completed. The catalog snapshot identifies the course and lists external resources, but their contents are not present here and were not inspected. You do not need them for this unit.

## Unit 1: Engineering a deterministic image k-NN baseline

Before working with larger vision models, you will turn a familiar algorithm into a reliable component. You will implement a brute-force k-nearest-neighbor classifier for flattened image vectors, expose it through a small command-line interface, and verify both mathematical behavior and software invariants.

The point is not to claim that k-NN is a deep-learning model. It is to establish an end-to-end baseline and a replaceable model boundary while practicing engineering habits that later experiments depend on.

Expected effort: **6–8 hours**.

## Learning outcomes

By the end of this unit, you should be able to:

- translate a distance-and-voting rule into a stable Python API;
- enforce lifecycle, shape, numeric, and non-mutation invariants;
- make ties and serialized output reproducible;
- test happy paths and adversarial boundaries without a network or external dataset;
- explain the implementation's time and space costs; and
- identify which interface can stay stable when a later classifier replaces k-NN.

## Assumed background

You should be comfortable with basic Python, vectors and matrices, calculus notation, and asymptotic analysis. No machine-learning library is required. The implementation must use only the Python standard library so that the result is reproducible in a clean environment.

## Material boundary

The learner-safe files in this directory are sufficient for the kickoff. Catalog-listed pages, videos, repositories, and the recommended textbook are discovery links only: they have not been fetched or verified and are not required. Do not obtain restricted, private, paywalled, solution, hidden-grader, or other access-controlled material for this work.

Completing the task produces evidence for this unit only. An external validator, not a self-report, decides whether that evidence satisfies the unit contract.
