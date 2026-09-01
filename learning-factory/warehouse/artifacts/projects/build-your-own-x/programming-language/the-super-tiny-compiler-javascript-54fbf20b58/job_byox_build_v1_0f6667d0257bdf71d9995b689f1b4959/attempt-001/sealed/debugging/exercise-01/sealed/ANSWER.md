# Exercise 01 answer: scanner progress

`ch` is captured before the whitespace branch increments `cursor`. Execution
then falls through and tests that stale whitespace character against the other
branches, finally reporting it as unexpected. The cursor did progress, but the
current iteration did not end when its token class was handled.

The local repair is to make whitespace consumption terminal for the iteration:

```js
if (isWhitespace(ch)) {
  cursor += 1;
  continue;
}
```

An `else if` chain can also prevent the immediate fall-through, but explicit
`continue` statements encode the useful invariant: every recognized branch
either consumes one or more source characters and starts a fresh iteration, or
returns a token through a helper with the cursor already advanced. The unknown
character branch must consume nothing and throw; silently incrementing there
would hide invalid input.

Regression coverage should include leading, internal, and trailing spaces;
mixed tab/newline/carriage-return spacing if those are in the lexical grammar;
empty and whitespace-only source; adjacent punctuation; and an actually unknown
character to show that error reporting was preserved. A defensive development
assertion can compare `cursor` at the top and bottom of a non-throwing iteration
to detect future non-progress loops.
