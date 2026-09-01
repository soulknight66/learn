# Build a Tiny Compiler: Pebble

Pebble is a deliberately small programming language with enough machinery to expose the real
decisions in a compiler: token boundaries, precedence, control flow, runtime state, bytecode
generation, and virtual-machine safety. Your task is to implement the same language twice: first as
a tree-walking evaluator, then as a compiler targeting a stack machine.

This challenge was independently authored from catalog metadata. The linked project recorded in the
administrator provenance snapshot is context only; it is not required, mirrored, or reproduced here.

## What you will build

Given this program:

```pebble
let remaining = 3;
while remaining > 0 {
  emit remaining;
  set remaining = remaining - 1;
}

if remaining == 0 {
  emit true;
} else {
  emit false;
}
```

both backends must produce the observable output `[3, 2, 1, true]`.

The pipeline is:

```text
source -> tokens -> AST -> tree evaluator
                    \-> bytecode -> stack VM
```

Read [REQUIREMENTS.md](REQUIREMENTS.md) for the normative contract and
[CONCEPTS.md](CONCEPTS.md) for the ideas behind it. The files in `starter/` define the implementation
surface. `public_tests/` contains a deliberately incomplete test suite.

## Progressive path

1. Tokenize punctuation, keywords, identifiers, numbers, and comments while preserving locations.
2. Parse statements and precedence-aware expressions into the specified AST.
3. Evaluate the AST with deterministic variable and type rules.
4. Lower that AST to deterministic stack bytecode with correct branch targets.
5. Execute bytecode defensively and make its results agree with the tree evaluator.
6. After the core is correct, request the debugging, review, adversarial, and benchmark stages from
   whoever administers the challenge. Those stages are intentionally outside the initial learner
   view.

Do not optimize before both backends agree on errors and results whenever neither backend exhausts
its documented work budget. Test exact budget cutoffs separately. Differential tests are much more
valuable here than clever bytecode.

The complete challenge pack contains administrator-controlled later-stage directories. Administrators
must transfer only a projection produced from `environment/view-policy.json`: it starts with a
default-deny `core` allowlist, adds prompt directories cumulatively, and excludes `sealed/` from every
stage. Never give a learner the complete administrator tree. Seeing later-stage names here is not
permission to bypass the configured reveal sequence.

## Running the visible checks

The project has no third-party runtime dependencies. With Node.js 20 or newer:

```bash
node --test public_tests/*.test.mjs
```

The provided starter is intentionally incomplete, so failures are expected until you implement its
TODOs. Neither the generation host nor the repair host contained Node.js; the administrator
validation record identifies the checks that could be performed here. Independent validation
remains required.

## Boundaries

- Implement only in `starter/` unless your challenge administrator says otherwise.
- Treat test inputs and bytecode as hostile data: no `eval`, `Function`, or shell execution.
- Do not inspect or copy sealed reference material while solving.
- Passing public tests is necessary, not sufficient. Edge cases and cross-backend parity are part of
  the contract.
