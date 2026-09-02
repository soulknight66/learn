# Productionization assessment

Status: **not productionized**.

Before deployment or use on untrusted input, at minimum:

- validate the existing nesting budget across target stacks or replace recursion with an iterative strategy;
- introduce dynamically sized, ownership-audited storage with allocation limits;
- split bytecode validation from execution and version any serialized format;
- decide atomic versus streaming output and handle all output failures consistently;
- add multiple-error recovery, source spans, stable diagnostic identifiers, and localization policy;
- add sanitizer jobs, coverage-guided fuzzing for lexer/parser/VM, mutation testing, and platform/ABI matrices;
- isolate execution with OS resource limits if the language gains loops, calls, or external effects;
- establish performance budgets with reproducible corpora and regression thresholds;
- complete security review, dependency/toolchain provenance, release signing, compatibility policy, and operational observability.

Local builds and deterministic tests do not satisfy those gates. No production-readiness, fuzzing, benchmark, security, or transfer label is claimed.
