# Public tests

These tests define a small, learner-visible sample of the contract. Run them from the repository
root with a current Node.js release:

```bash
node --test public_tests/*.test.mjs
```

The untouched starter is expected to pass lexer checks and fail checks that reach an explicit
`TODO`. Do not edit these tests to make that baseline green. Implement the missing stages and add
your own tests for cases not revealed here, especially malformed syntax, nested scopes, jump
boundaries, and backend error parity.

Passing this suite alone is not a completion claim. Instructor validation may use different source
programs and malformed bytecode.
