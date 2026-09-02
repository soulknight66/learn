# Sealed reference implementation

`compiler.js` is the dependency-free CommonJS oracle for Ripple. It implements every public phase, uses semantic binding IDs during generation, and evaluates the AST independently in `interpret`.

Reference-only commands, from the repository root on Node.js 18+:

```text
node --check sealed/reference/compiler.js
node --test sealed/reference_tests/compiler.test.js
node sealed/reference/cli.js starter/example.ripple
node sealed/reference/cli.js --emit-js starter/example.ripple
```

The CLI returns 2 for bad arguments and 1 for a structured source diagnostic. It is reference tooling and is not part of the learner API.
