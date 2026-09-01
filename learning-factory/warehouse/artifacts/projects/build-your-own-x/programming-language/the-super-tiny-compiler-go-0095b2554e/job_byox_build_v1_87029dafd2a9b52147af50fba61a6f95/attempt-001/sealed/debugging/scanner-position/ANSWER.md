# Scanner-position answer

The likely bug resets the column on carriage return and then treats the following line feed as an ordinary byte (or increments immediately after resetting). Pebble's contract gives only LF newline semantics: CR is whitespace that advances the current column, and LF increments the line and sets the next byte's column to 1. Processing the pair in the opposite roles places `(` at column 2.

LF-only tests can miss a CR-specific branch. A regression table should include `"\rX"` (X remains line 1, column 2), `"\nX"` (2:1), `"\r\nX"` (2:1), and multiple CRs before LF. Assert both zero-based byte offsets and line/column for X and EOF.
