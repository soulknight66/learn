# UCB EE120: Signal and Systems — kickoff brief

Preparation label: **manager-authored kickoff; not an official EE120 unit and not yet independently validated**.

## What this is

This is an eight-hour first study unit for a student who is already comfortable with algorithms and wants stronger software-engineering habits. You will turn a small mathematical model—finite discrete-time signals and linear convolution—into a specified, tested, and measured Python component.

The supplied catalog describes UC Berkeley EE120, names Python, and mentions six applied labs. It does not supply the recordings or assignment content. Those materials were not retrieved, and this packet does not recreate or claim equivalence to an EE120 lecture, assignment, or lab. Completing this kickoff does not complete the course.

## Unit at a glance

- **Title:** Finite Discrete-Time Signals and Reliable Convolution Software
- **Time box:** 8 hours
- **Tools:** Python 3 standard library, including `unittest`; no network resource is required
- **Main idea:** Make indexing, edge cases, correctness evidence, and performance claims explicit
- **Outputs:** A small module, tests, a benchmark, machine-readable evidence, an engineering report, and written comprehension responses

The work stops at finite real-valued signals, shifts, and linear convolution. FFTs, continuous-time systems, sampling, frequency response, control, and the catalog's labs are outside this unit.

## Why this unit fits an algorithms student

Convolution has a compact mathematical definition, but reliable software still requires decisions that an asymptotic analysis does not settle: data representation, index conventions, empty inputs, invalid numeric values, independent oracles, floating-point comparison, benchmark design, and reproducible evidence. The goal is to practice those decisions on a bounded problem.

By the end of the unit, you should be able to:

1. Translate an indexing convention into an unambiguous API contract.
2. Implement direct and sparsity-aware convolution with the same observable behavior.
3. Combine examples, invariants, and deterministic generated cases into a useful test suite.
4. Distinguish a complexity argument from a benchmark observation.
5. Hand another engineer enough code, evidence, and provenance to reproduce your result.

## Readiness check

You should know Python classes and functions, `unittest`, and Big-O/Theta notation. Familiarity with arrays and summations is useful. The source catalog lists CS61A, CS70, calculus, and linear algebra as course prerequisites, but this kickoff needs only the narrower skills above.

If discrete-time indexing is new, use this operational model: a signal has samples at consecutive integer indices and has value zero outside that finite interval. The exact representation and behavior required for this unit are specified in [STUDY_TASK.md](STUDY_TASK.md).

## Material status

This local learner packet is sufficient for the bounded task. The catalog provides locators for an EE120 Fall 2019 website and a GitHub repository, but their contents were not retrieved or verified. Recordings and assignments are only described as being on the course website and are unavailable here. Do not assume that a catalog record is itself an official course unit.

## What completion means

Submit every artifact named in the task and make it reproducible from the documented commands. A harness-controlled validator and an independent examiner determine whether this unit is complete. Your report, passing local tests, or this preparation note alone cannot promote job state. Even a validated submission means only **kickoff unit complete; course still in progress**.

Proceed to [STUDY_TASK.md](STUDY_TASK.md), then answer the questions in [COMPREHENSION.md](COMPREHENSION.md).
