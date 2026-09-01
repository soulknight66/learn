# MIT 6.031: Software Construction — Kickoff Brief

## What this packet is

This is a self-contained, manager-authored kickoff inspired by the catalog description of MIT 6.031. It is not an official MIT unit, problem set, or substitute for the course. Completing it establishes evidence for this one study unit only; it does not complete the roughly 100-hour course.

The catalog describes high-quality software using three goals:

- safe from bugs;
- easy for another programmer to understand; and
- ready for change.

You will apply all three to a small Java abstract data type whose underlying algorithm should be manageable for a strong algorithms student. The challenge is to make the behavior precise, preserve an abstraction boundary, test it convincingly, and then change it safely.

## Unit at a glance

**Unit:** From a Correct Algorithm to a Trustworthy ADT  
**Timebox:** 6–8 hours  
**Language:** Java  
**Starting point:** You should already be comfortable implementing and analyzing basic data structures and writing automated tests.

By the end of the unit, you should be able to:

1. state a public contract independently of an implementation;
2. document an abstraction function and representation invariant;
3. protect the representation from invalid inputs, overflow-related boundary mistakes, and aliases;
4. combine focused examples with model-based tests; and
5. absorb one explicit requirement change while preserving earlier behavior.

## Boundaries

The first unit covers one interval-set ADT, its tests, a short design note, a small change log, and written comprehension responses. It does not cover concurrency, parallel programming, large-system architecture, or any official 6.031 assignment.

No external reading or recording is required. The catalog links several MIT course sites, but those pages were not retrieved or verified for this packet. The catalog reports no recordings and gives only an aggregate description of “4 Problem Sets + 1 Project”; their contents are not present here.

## Suggested workflow

Read `STUDY_TASK.md` completely before coding. Work contract-first, keep baseline tests passing as you implement the change request, and answer `COMPREHENSION.md` only after reviewing your final code. Put your work in your learner workspace, not inside this packet.

Keep build and test output. Completion must be determined from submitted artifacts and validator/examiner evidence, not from a statement that the work is done.
