# CMU 11-785 Kickoff Brief

## What this package is

This is a bounded, eight-hour kickoff inspired by the catalog description of **CMU 11-785: Introduction to Deep Learning**. It is designed for a learner who is already comfortable with algorithms, linear algebra, probability, Python, and basic machine learning, and who wants stronger software-engineering practice.

The kickoff is manager-authored. It is not presented as a CMU lecture, homework, or official syllabus unit. Completing it records progress on this unit only; it does not complete CMU 11-785 or the catalog's roughly 120-hour course.

## First-unit outcome

You will turn a compact mathematical contract for a two-layer neural classifier into tested numerical software. By the end, you should be able to:

- make tensor shapes and failure behavior explicit;
- implement forward computation, analytic gradients, and a parameter update without automatic differentiation;
- test numerical code deterministically, including with finite differences and extreme inputs; and
- report a small experiment with enough configuration and provenance for another person to reproduce it.

The emphasis is not on writing many lines of model code. It is on making a small implementation trustworthy.

## Suggested time box

| Phase | Target time |
|---|---:|
| Contract review and gradient derivation | 1.5 hours |
| Implementation | 2.5 hours |
| Tests and defect fixing | 2 hours |
| Experiment, reflection, and comprehension responses | 2 hours |

Stop after the bounded deliverables are complete. Record unresolved defects or questions rather than silently expanding the assignment.

## Material status

The provided catalog snapshot names a public course-site link and describes recordings, notes/slides, readings, programming assignments, and a project. None of that external course content is bundled with this kickoff, and the course site was not fetched while preparing it. The study task is therefore self-contained and does not require unavailable material.

Future units may use independently verified public materials, but only after their identity, semester, access terms, and contents are recorded. A catalog record or link alone is not treated as an official unit.

## Completion boundary

Prepare every deliverable named in `STUDY_TASK.md`, run the documented clean test command, and submit your comprehension responses. An independent examiner determines whether this kickoff unit passes. Your own completion statement, a passing test suite by itself, or finishing this one unit cannot establish whole-course completion.
