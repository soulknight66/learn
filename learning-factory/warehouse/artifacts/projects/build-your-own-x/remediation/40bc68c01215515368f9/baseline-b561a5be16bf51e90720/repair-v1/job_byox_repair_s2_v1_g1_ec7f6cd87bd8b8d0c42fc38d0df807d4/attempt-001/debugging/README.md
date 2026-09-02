# Debugging exercise: the disappearing condition

Given a compiler variant where `if (true) print 1; else print 2;` underflows the stack only when an
`else` exists, draw stack shapes at the condition, conditional jump, each `POP`, and merge point. Locate
the first instruction at which branch stack heights diverge. Keep the diagnosis and patch in this
exercise's `sealed/` area; do not place the answer here.
