# Sealed reference implementation

Evaluator-only original implementation of the Sprout contract. It uses no third-party packages and
exports the same API as the starter. Run from this directory with `npm test` on Node.js 20 or newer.

The original modules were not executed because the generation host exposed no compatible
Node.js/ES-module runtime. A mechanically downleveled GJS smoke bundle exercised core algorithms, but
does not validate ESM linkage or Node behavior. Independent validation is required.

Repair generation 1 addresses independently reported keyword-prototype collisions, untrusted array
prototype handling, and flat-expression recursion. The regressions remain unexecuted as original
Node modules on this host; see the production validation record for the bounded transformed check.
