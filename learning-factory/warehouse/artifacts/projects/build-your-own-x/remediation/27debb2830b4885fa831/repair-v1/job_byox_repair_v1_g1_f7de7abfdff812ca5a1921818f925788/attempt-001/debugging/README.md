# Debugging exercises

`precedence/` contains a small, deliberately faulty infix-to-postfix helper and a focused failing
test. Diagnose the behavior without changing the assertions. Record the invariant that was violated,
the smallest reproducer, and why the correction covers all operators in the helper.

Evaluator answers and corrected code are kept only in the mirrored
`sealed/debugging/precedence/` directory.

The local package marker makes both the exercise module and its `.js` test entry point explicit
ECMAScript modules on every supported Node.js release.
