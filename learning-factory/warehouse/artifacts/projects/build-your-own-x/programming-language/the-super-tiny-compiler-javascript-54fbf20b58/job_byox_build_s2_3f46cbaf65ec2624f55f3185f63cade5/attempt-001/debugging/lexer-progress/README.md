# Exercise: the scanner that stalls

Run:

```text
node --test debugging/lexer-progress/buggy.test.js
```

`scan` is a deliberately reduced scanner. The test expects four punctuation tokens but receives a `SCANNER_STALLED` error. Trace `index` and `steps` for the first character.

Constraints:

- Preserve token values and the `maxSteps` guard.
- Every successful outer-loop iteration must consume at least one UTF-16 code unit.
- Unknown input must throw with its offset.
- Add table-driven coverage for `(`, `)`, `,`, and `;`.

Write your diagnosis before editing. The exercise answer belongs only in this exercise's sealed material.
