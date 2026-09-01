# Adversarial validation guide

This directory contains solution-free cases for a later independent validator. Exercise at least these families:

- very long identifiers, comments, decimal literals, unary chains, and nesting;
- every one-character prefix of a two-character operator at end of input;
- missing delimiters and semicolons at every grammar boundary;
- same-scope redeclaration, nested shadowing, and references just outside scope;
- false loop entry, many loop iterations, and a deliberate infinite loop;
- 32-bit boundaries for every arithmetic operation and all divisor sign pairs;
- booleans supplied to every integer operator and integers supplied to boolean sites;
- unknown opcodes, wrong arities, bad jump targets, uninitialized locals, underflow, fallthrough, and leftover stack values.

The sealed reference suite covers representative members, but this artifact makes no fuzzing claim. A later fuzzer should record its seed, generator version, case count, time bound, minimized failures, target commit, and an explicit independent-validation label.
