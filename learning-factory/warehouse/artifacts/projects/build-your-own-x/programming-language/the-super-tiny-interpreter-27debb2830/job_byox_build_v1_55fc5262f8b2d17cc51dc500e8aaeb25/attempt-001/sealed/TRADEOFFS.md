# Tradeoffs

## Plain objects versus classes

Plain token, AST, and bytecode records are easy to inspect and compare. They require explicit shape
validation and provide less encapsulation than classes. The implementation uses classes only for
errors, scanner/parser state, and runtime environments.

## Shared semantics versus independent engines

Sharing arithmetic and truthiness helpers prevents routine drift, but differential tests cannot catch
a defect shared by those helpers. Contract-based unit tests must independently pin each operator.

## Absolute jumps versus labels

Absolute indexes keep VM dispatch small and make the serialized format explicit. They make insertion
after compilation unsafe. The compiler therefore patches forward jumps only while building code and
returns no mutable label objects.

## Fail-fast parsing versus recovery

Fail-fast errors are deterministic and keep this project focused. An editor-facing implementation
would benefit from synchronization and multiple diagnostics, which would complicate both API and
tests.

## Per-engine step counters

Counting AST visits and instruction dispatches is easy to audit and deterministically stops loops.
The same numeric budget does not represent equal semantic work. A production quota might use a
weighted source-level cost model shared by compiler and evaluator.

## Strict bytecode records

Rejecting extra fields catches corruption and ambiguous formats early. It also prevents compatible
extension without a version change; that is intentional for version 1.

## Recursive AST phases

Recursive descent and recursive evaluation are readable for a tiny language. Even with explicit
depth limits, host stack capacity varies. A hardened implementation would use iterative frames for
deep untrusted trees.
