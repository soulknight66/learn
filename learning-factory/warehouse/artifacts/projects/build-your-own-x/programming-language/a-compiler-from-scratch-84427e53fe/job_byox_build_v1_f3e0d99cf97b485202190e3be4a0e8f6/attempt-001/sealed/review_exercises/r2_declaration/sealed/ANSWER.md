# R2 answer

`let x = x;` must fail when there is no outer `x`; early insertion can turn it into an uninitialized self-reference. `let x = 1; if (true) { let x = x + 1; print x; }` must print `2`; early insertion makes the initializer select the new binding rather than outer slot 0. Check same-scope duplicates before compiling, but insert the new binding only afterward.
