# NJU Software Analysis — Kickoff Brief

## Your starting point

This is one bounded kickoff unit, not the full NJU Software Analysis course. The catalog describes a roughly 60-hour course spanning static-analysis foundations, data-flow analysis, pointer analysis, security applications, and advanced topics such as IFDS. Here you will work only on the first engineering foundation: representing a small intermediate language, building its control-flow graph (CFG), and analyzing graph reachability.

The unit is designed for a student who is already comfortable with algorithms but wants stronger software-engineering practice. Expect about 8 focused hours, with a reasonable range of 6–10 hours. Stop at the stated boundary rather than growing the tool into a compiler or a full data-flow framework.

## Why this unit comes first

Static analysis answers questions about programs without running those programs. Before more advanced analyses can be implemented, their input must have precise structure. An abstract syntax tree preserves source-language structure; an intermediate representation (IR) exposes operations in a form suited to analysis; and a CFG makes possible transfers of control explicit. A bug in any of these contracts contaminates every later analysis.

Your project therefore emphasizes four habits:

- translate a compact specification into explicit data-model invariants;
- keep parsing, validation, graph construction, and reporting separate;
- make all observable output deterministic;
- use tests to preserve evidence, including for malformed input.

## Unit outcomes

By the end of this unit, you should be able to:

1. distinguish source syntax, IR, and CFG responsibilities;
2. validate a small block-based IR without silently repairing it;
3. derive successor and predecessor relations and entry reachability;
4. provide stable command-line behavior and actionable diagnostics; and
5. defend the design with focused automated tests and written reasoning.

## Materials and access

The catalog snapshot contains links to a lecture website, a Bilibili video, an assignment overview, and an online judge. These links were not fetched or verified for this unit, and the catalog explicitly lists no textbook. None of them is required: the task specification is self-contained and can be completed offline with your local language toolchain.

Treat remote links as optional leads, not as proof of an official sequence or available content. Do not bypass a login or other access control, and do not seek restricted tests or solutions.

## Completion boundary

Complete the implementation, tests, short design note, and responses requested in the accompanying files. An independent evaluator—not a self-report—determines whether this kickoff unit is complete. Completing it does not establish completion of any later topic or of the whole course.

---

Provenance: learner-safe, manager-authored kickoff derived only from the supplied CSDIY catalog snapshot at source commit `adce8e13789dc16aa6d1fbe163e9541736defae4`. No linked content was retrieved. This unit does not claim official NJU authorship or endorsement.
