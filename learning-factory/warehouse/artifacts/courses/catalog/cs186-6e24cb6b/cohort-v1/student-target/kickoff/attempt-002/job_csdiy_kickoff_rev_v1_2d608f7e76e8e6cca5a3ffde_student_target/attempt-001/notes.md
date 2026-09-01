# Revision Learning Notes

Unit: `managed_unit_01_relational_pipeline`  
Status: learner-generated revision; source present, not compiled or evaluator-validated

## Scope

This revision addresses only the supplied manager-authored in-memory operator kickoff. It implements
scan, filter, project, and limit plus their typed data and lifecycle contracts. It does not implement
SQL, joins, disk storage, indexes, optimization, concurrency, recovery, NoSQL, or any other CS186
unit. Nothing here claims course completion.

## What changed after feedback

The failed prior package contained narrative claims but no executable tree. I created a fresh,
identifiable submission tree in this workspace:

- 21 production Java files under `src/main/java/edu/learningfactory/relational/`;
- one dependency-free test runner under the separate `src/test/java/...` tree;
- `DESIGN.md`, `RUN.md`, `COMPREHENSION_RESPONSE.md`, and `SUBMISSION_MANIFEST.json`;
- `artifact-inventory.txt` and `SUBMISSION_SHA256SUMS.txt` for file identity; and
- a fresh `test-output.txt` from the documented command.

The inventory names 32 submitted paths. The checksum file covers the 22 Java files and five stable
contract/provenance inputs; its own SHA-256 in the captured attempt is
`38732dfea0a0625bea7298b3d5e903c7c1e8da0b51cb1f38f5caf3335855ee79`. The mutable run log and these
revision records are intentionally inventoried but not placed inside the self-identifying checksum
set.

## Contract summary

`Schema` and `Row` copy caller collections and expose immutable views. Values are exactly `Integer`
or `String`, never null. `PullResult` separates rows from EOS. Structural schema equality allows
separately constructed but equivalent metadata while rejecting differences in name, type, or order.

`AbstractOperator` supplies a single-use `NEW -> OPEN -> EXHAUSTED -> CLOSED` lifecycle, with direct
early `OPEN -> CLOSED`. EOS is stable and does not trigger another source pull. The state becomes
`CLOSED` before cleanup, so repeated close cannot execute a cleanup hook twice. A failed open performs
one rollback, retains the original exception, and suppresses a distinct cleanup exception.

Unary operators own their child exclusively through the `Operator` interface. Filter binds and checks
its predicate before opening. Project binds a nonempty distinct column list and constructs the output
schema in requested order. Limit checks its bound before asking its child, which makes zero-limit and
no-over-pull behavior observable.

## Verification design

The test main has 13 deterministic groups. Beyond output equality, counting test operators observe
source pulls and closes. Coverage includes individual operators, all four composed, stable ordering,
none/some/all filters, every supported predicate, projection metadata, four limit boundaries, schema/
type/predicate/argument failures, lifecycle misuse, repeated EOS, normal and early close, failed-open
rollback, caller alias mutation, Unicode strings, integer extrema, and a fixed-seed list oracle.

The generated test computes expected `(tag, id)` values from plain records before constructing any
production predicate or operator. An independent emulation of `java.util.Random` found 102 qualifying
records among 240, so the expected list can genuinely reach its limit of 37.

## Evidence boundary

Static checks found 22 Java files, balanced nested delimiters, matching public type/file names, only
expected `java.util` imports, valid manifest JSON, and exact manifest/inventory agreement. All 27
entries in `SUBMISSION_SHA256SUMS.txt` verify.

The fresh clean command still cannot compile in this workspace: no `javac`, `java`, `jshell`, ECJ,
GCJ, Ant, Maven, or Gradle command is available. `test-output.txt` records the exact compiler argv,
digest identity, `javac: command not found`, and exit status 127. Therefore the Java syntax/type checks
and all authored assertions remain unexecuted hypotheses, not pass evidence.

## Next bounded experiment

Provide a JDK 8-or-newer on the worker `PATH` and run `RUN.md` unchanged. Compiler diagnostics come
first; only after compilation should the 13 groups be interpreted. Repeat from another fresh
`mktemp` directory if the first run passes. A worker-controlled evaluator must independently validate
the same digest before any pass label is assigned; this revision makes no transfer or validation
claim.
