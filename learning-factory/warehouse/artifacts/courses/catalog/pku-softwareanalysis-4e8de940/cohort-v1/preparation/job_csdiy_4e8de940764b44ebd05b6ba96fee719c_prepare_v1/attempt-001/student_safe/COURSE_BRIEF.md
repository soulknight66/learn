# PKU Software Analysis: Kickoff Brief

Validation label: LEARNER_SAFE · PREPARED_AWAITING_INDEPENDENT_VALIDATION

## What this course record supports

The catalog describes a roughly 60-hour, advanced Peking University course covering data-flow and interprocedural analysis, pointer analysis, abstract interpretation, SAT/SMT and symbolic execution, and applications such as synthesis and repair. It assumes data structures and algorithms plus fluency in at least one programming language.

The catalog does not provide a verified lecture sequence or a textbook. Its website and video entries are links only and were not fetched or checked while this packet was prepared. Accordingly, this packet starts with one locally authored unit grounded in the catalog's explicit data-flow-analysis topic. It is not represented as an official PKU lecture or assignment.

## Your bounded first unit

**Unit:** Engineering a Deterministic Reaching-Definitions Analyzer  
**Timebox:** 8 hours  
**Implementation language:** Python 3.11 standard library  
**Primary task:** Build, test, and explain a small intraprocedural forward may-analysis over a supplied JSON intermediate representation.

This is deliberately a software-engineering unit as well as an algorithms unit. A correct fixed-point equation is only part of the work. Your program must also have a clean boundary between input handling and analysis, deterministic behavior, useful validation failures, automated tests, and an honest account of limitations.

By the end of the unit, you should be able to:

- turn reaching-definitions equations into a terminating worklist implementation;
- explain joins, redefinitions, loops, and the finite-height convergence argument;
- separate the analysis core from the command-line and JSON layers;
- test both semantic behavior and operational behavior;
- distinguish a may fact from a definite-initialization guarantee.

## Scope boundary

Included here are a small control-flow graph, single-variable definitions, statement-level uses, forward union joins, deterministic serialization, failure handling, and tests.

Not included are source-language parsing, interprocedural calls, aliases, pointers, heap objects, exceptional control flow, widening, constraint solving, synthesis, or the catalog's larger Java pointer-analysis and program-synthesis projects. Those topics require later units and independently verified materials.

## Material status

The three files in this learner packet are sufficient for the kickoff:

- COURSE_BRIEF.md gives context and boundaries.
- STUDY_TASK.md is the complete implementation contract.
- COMPREHENSION.md contains the questions you must answer.

The catalog also lists the following optional pointers:

- 2020 course homepage: https://xiongyingfei.github.io/SA/2020/main.htm
- Professor homepage: https://xiongyingfei.github.io/
- 2020 video portal: https://liveclass.org.cn/cloudCourse/#/courseDetail/8mI06L2eRqk8GcsW

These links are unverified and not required. Reachability, access conditions, licensing, and contents are unknown in this preparation. Do not treat visiting a link as completion evidence. No course textbook is available in the catalog snapshot.

## Suggested eight-hour rhythm

1. **Model and examples — 1 hour:** Restate the domain and transfer operation and work small graphs by hand.
2. **Analysis core — 2 hours:** Implement reachability, predecessors, statement transfer, and fair worklist convergence.
3. **Boundary engineering — 1.5 hours:** Add complete input validation, stable diagnostics, and atomic deterministic output.
4. **Verification — 2 hours:** Build focused tests for paths, joins, loops, unreachable blocks, and bad inputs.
5. **Reasoning and cleanup — 1.5 hours:** Answer the comprehension prompts, document design choices, and run the clean test command.

Stop at the timebox and record any known gap honestly rather than silently broadening the task.

## Completion boundary

Producing files or reporting that the analyzer works does not complete this unit. Independent execution and review must establish the result. Even a validated pass completes only this kickoff; it cannot establish completion of the full Software Analysis course.

## Provenance

This learner-safe packet was authored by the learning-factory course manager from CSDIY catalog snapshot commit adce8e13789dc16aa6d1fbe163e9541736defae4, catalog content SHA-256 5c26f67523735d0b6f94bd684d945d637207e18ad98e7ca8268df6c70bc434fd. No linked remote content was retrieved or reproduced.
