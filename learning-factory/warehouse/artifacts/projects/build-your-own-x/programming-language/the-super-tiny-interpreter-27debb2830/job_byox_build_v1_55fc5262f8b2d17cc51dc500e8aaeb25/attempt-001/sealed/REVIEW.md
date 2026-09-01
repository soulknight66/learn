# Generation-time implementation review

Status: source review only. No compatible Node.js/ES-module runtime was available, so none of these findings constitutes
a tested or reviewed validation label.

## Positive observations

- Language output is accumulated in returned arrays; the runtime does not touch console, filesystem,
  network, subprocess, dynamic evaluation, or ambient environment state.
- Compiler control-flow shapes maintain a one-result invariant, and the VM independently checks join
  stack/scope depths before dispatch.
- Both evaluators share type, arithmetic, truthiness, equality, and formatting rules.
- Source, tokens, recursion, instructions, constants, stack, scopes, and execution all have finite
  default ceilings that callers may only lower.

## Known gaps before production use

- `parse` assumes tokens came from the lexer and does not deeply validate every token record. A
  malicious hand-built token array can receive a less specific parse error.
- Tree interpretation and compilation accept plain AST objects without a complete preflight schema
  walk. Cyclic or accessor-bearing objects are outside the safe input boundary.
- String concatenation has no result-size quota, so a short doubling loop can consume substantial
  memory before the step budget expires.
- JavaScript proxies/accessors cannot be made inert by ordinary shape checks. Production input should
  be decoded from a bounded serialization into fresh data before validation.
- Diagnostics and stack safety have not been exercised across supported Node.js releases.
- No fuzzing, coverage measurement, mutation testing, profiling, or benchmarks were run here.

## Required follow-up

Run the sealed test suite on Node.js 20 and a current LTS, add a bounded JSON decoder for external
bytecode, impose value/output byte quotas, fuzz lexer/parser/validator boundaries, and independently
audit denial-of-service behavior before considering deployment.
