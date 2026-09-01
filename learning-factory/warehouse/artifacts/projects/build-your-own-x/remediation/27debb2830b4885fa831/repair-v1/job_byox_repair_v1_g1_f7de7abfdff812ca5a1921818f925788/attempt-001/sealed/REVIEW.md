# Repair-generation implementation review

Status: source review plus transformed supplemental smoke only. No compatible Node.js/ES-module
runtime was available, so none of these observations constitutes a tested or reviewed validation
label.

## Repairs made after independent review

- Keyword recognition now uses a frozen null-prototype table plus an own-property lookup, with
  regressions for `constructor`, `toString`, `hasOwnProperty`, and `__proto__`.
- Bytecode validation rejects null, subclass, and custom array prototypes before element reads and
  never calls an inherited method on the untrusted code array.
- The compiler and tree interpreter walk left-associative binary/logical spines iteratively; sealed
  regressions cover 999, 1,000, and 1,001 addition terms and a long logical chain.
- Local package markers make every import-bearing `.js` tree explicitly ECMAScript-module scoped.
- `environment/learner_view.py` defines an exact learner allowlist and gives a trusted harness
  non-merging export plus exact-copy verification. Generation ran only its no-output policy check.
- The contract now explicitly permits grouped identifier assignment and excludes engine-local
  step-budget boundaries from otherwise exact tree/VM parity.

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

Run the sealed test suite on the oldest supported Node.js 20 release and a current LTS, have the
worker harness export and independently inspect a learner view, add a bounded JSON decoder for
external bytecode, impose value/output byte quotas, fuzz lexer/parser/validator boundaries, and
independently audit denial-of-service behavior before considering deployment.
