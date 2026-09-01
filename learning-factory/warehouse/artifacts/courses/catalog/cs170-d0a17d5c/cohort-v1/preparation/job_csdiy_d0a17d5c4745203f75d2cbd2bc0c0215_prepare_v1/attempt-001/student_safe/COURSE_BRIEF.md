# CS170 kickoff: from an algorithm to dependable software

This packet opens a bounded study unit aligned with the catalog's divide-and-conquer and complexity-analysis themes. It is manager-authored, not an official UC Berkeley assignment. Finishing it completes only this kickoff unit, not CS170 or any later course topic.

## The engineering problem

An inversion is a pair of positions `i < j` whose values are out of order: `values[i] > values[j]`. Inversion counts appear in ranking comparisons and disorder metrics. The mathematical definition is short; a trustworthy component still needs an exact contract, a scalable algorithm, correct handling of duplicates, stable command-line behavior, meaningful tests, and reproducible evidence.

You will build such a component in Python 3.11. Your implementation must achieve worst-case `O(n log n)` time, leave its input unchanged, and expose both a Python API and a small JSON command-line interface. You will support the implementation with tests, a design argument, and a benchmark whose limitations are stated honestly.

## Learning goals

By the end of this unit, you should be able to:

- translate a mathematical relation into observable API behavior;
- connect an implementation invariant to a correctness argument;
- distinguish a complexity proof from empirical timing evidence;
- use a simple reference implementation as a test oracle without putting it in production;
- test pure behavior, mutation boundaries, error behavior, and process-level interfaces;
- leave another engineer enough commands and context to reproduce your work.

## Scope and timebox

Plan for about seven hours and stop after eight. A reasonable split is one hour for design and contract work, two hours for implementation, two hours for tests, one hour for benchmarking, and one hour for explanation and cleanup. Record any attractive extensions as follow-up work instead of expanding this unit.

The provided learner-safe files are sufficient. The catalog mentions a website, recordings, assignments, and a textbook, but their contents were not retrieved for this job. None is required here.

## Working posture

Treat every claim as something a reviewer should be able to inspect or rerun. Prefer a small clear module over a framework, deterministic inputs over unexplained randomness, and explicit limitations over broad claims. Use only the Python 3.11 standard library so the result remains portable.

Proceed to `STUDY_TASK.md` for the build contract. Answer `COMPREHENSION.md` after the implementation and evidence are complete.
