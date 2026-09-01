# Exercise 01: scanner progress

The scanner below reports an unexpected-character error whenever otherwise
valid source contains spacing between two tokens. Source with no spacing can
appear to work.

```js
while (cursor < source.length) {
  const ch = source[cursor];

  if (isWhitespace(ch)) {
    cursor += 1;
  }

  if (isDigit(ch)) {
    scanNumber();
    continue;
  }

  if (isIdentifierStart(ch)) {
    scanIdentifier();
    continue;
  }

  if (scanPunctuation(ch)) {
    cursor += 1;
    continue;
  }

  throw syntaxError(`Unexpected character ${ch}`, cursor);
}
```

Tasks:

1. Trace one loop iteration starting on whitespace and identify which values
   are stale after the cursor changes.
2. State a progress invariant for every successful scanner branch.
3. Repair the control flow without silently ignoring unknown characters.
4. Propose regression coverage for leading, internal, trailing, and
   whitespace-only input.

The answer should explain why merely moving the final error into an `else`
chain is more brittle than making token-consumption branches explicit.
