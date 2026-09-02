# Review findings

## High: source spelling is emitted as syntax

`emitDeclaration('x = 0; throw Error("owned"); const y', '1')` produces multiple executable statements. Even if the ordinary scanner currently limits identifiers, this module claims an AST boundary and cannot assume every caller used that scanner. Deserialization, plugins, tests, or future grammar changes can bypass the assumption.

## High: valid source-style names can be invalid JavaScript bindings

Names such as `class`, `await`, or `yield` can be accepted by a broader source grammar but make emitted code fail or change behavior depending on context. A blacklist is brittle across ECMAScript versions and output contexts.

## Medium: runtime collisions and inconsistent mapping

A declaration named like an emitter helper can shadow or conflict with generated support code. Separately sanitizing declarations and reads can also cause two names to collide or a read to target the wrong declaration.

## Remediation

Semantic analysis should assign each declaration an opaque integer binding ID and map each identifier use to that same ID. The backend emits only a fixed prefix plus a validated integer, such as `v_0`. Source spelling is retained solely for diagnostics. Built-ins and runtime helpers come from closed backend tables, not the source namespace.

Tests should include reserved words, `constructor`, `__proto__`, helper spellings, punctuation-bearing handcrafted AST names, two near-colliding source names, and declaration/read consistency. Assertions should inspect generated syntax and execute it only inside a test boundary.
