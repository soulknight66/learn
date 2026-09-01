# Answer: scroll over-read

At `row == height - 1`, the source row is `height`, so the first source index is exactly
`width * height`, one past the supplied extent. The copying invariant must be “source row is in
`[1, height)` and destination is source minus one.” Therefore copying stops before `row == height`;
the final valid row is blanked separately.

For a `2x2` surface, place a guard before and after four cells, fill row zero with `A,B` and row one
with `C,D`, trigger a scroll, then require row zero `C,D`, a blank row one, and unchanged guards. An
out-of-range read is undefined behavior even if its copied destination is blanked moments later.
