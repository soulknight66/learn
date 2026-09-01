# NJU Compilers: Engineering Kickoff

> Artifact classification: learner-safe, course-manager-authored study guide  
> Validation label: prepared for study; not yet validated as completed  
> Provenance: synthesized from the CSDIY catalog snapshot at commit `adce8e13789dc16aa6d1fbe163e9541736defae4`; no external course content was retrieved

## What this unit is

This is an 8–10 hour first study unit for a learner who is already comfortable with algorithms and now wants to strengthen day-to-day software-engineering practice. You will build one thin but complete compiler-front-end slice: a Java command-line program that uses ANTLR 4 to recognize a tiny expression language and emit a deterministic abstract-syntax representation.

The catalog describes an NJU course that combines compiler theory with Java and ANTLR 4 practice. This kickoff follows that general direction, but it is manager-authored. It is not presented as NJU's first official unit or as a copy of an NJU assignment.

## Outcomes

By the end of this unit, you should be able to:

- translate a compact language contract into lexer and parser behavior;
- explain how precedence, associativity, and end-of-input affect correctness;
- keep generated parser sources separate from authored application code;
- produce repeatable builds, deterministic output, and useful failures;
- design tests around boundaries and failure modes, not just happy paths; and
- connect claims in a design note to concrete source files and test cases.

## Starting point

You should know basic Java and command-line development. Discrete mathematics is the catalog prerequisite; familiarity with trees, recursion, and asymptotic reasoning will help. Prior ANTLR experience is not assumed.

The local materials for this kickoff are this brief, `STUDY_TASK.md`, and `COMPREHENSION.md`. The official website, recordings, textbook, and assignment details are not present locally and are not required. If you use an external tutorial, record it in your design note, but do not copy a solution.

## Engineering emphasis

Treat the grammar as one component in a small maintained system. A credible result must build outside an IDE, pin compatible tool and runtime versions, consume the whole input, own its diagnostics, and include automated tests. The goal is not merely to make several examples parse; it is to leave another engineer a small project they can understand, build, test, and extend.

## Boundary

This unit stops after syntax and stable AST-shaped output. It does not include type checking, evaluation, intermediate representations, optimization, code generation, runtime environments, or register allocation. Finishing it is evidence only for this kickoff after independent validation. It is never evidence that the full course is complete.
