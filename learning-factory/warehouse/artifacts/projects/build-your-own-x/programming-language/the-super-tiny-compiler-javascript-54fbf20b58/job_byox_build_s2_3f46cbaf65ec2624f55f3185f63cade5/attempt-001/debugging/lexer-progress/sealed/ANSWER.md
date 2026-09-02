# Diagnosis

The punctuation branch appends a token but never increments `index`. The next outer-loop iteration observes the same character, appends it again, and repeats until the diagnostic step budget fires. That violates the scanner's progress invariant: every non-throwing iteration must consume input.

Increment `index` exactly once after capturing the token's original offset. The whitespace branch already advances and the unknown-input branch throws, so no other branch needs a change. `fixed.test.js` covers each punctuation spelling independently as well as the mixed sequence.
