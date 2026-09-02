# Adversarial validation

The adversarial suite is sealed so it cannot become a checklist tailored into the learner implementation. It probes progress guarantees, source-location accounting, reserved and prototype-like names, string-to-code boundaries, short-circuit exceptions, deep/large expressions, and compile-size limits.

On Node.js 18+:

```text
node --test sealed/adversarial/compiler.adversarial.test.js
```

These cases are deterministic. The suite was not run on the generation host because Node.js was unavailable, and this artifact does not claim `FUZZED` or any stronger validation label.
