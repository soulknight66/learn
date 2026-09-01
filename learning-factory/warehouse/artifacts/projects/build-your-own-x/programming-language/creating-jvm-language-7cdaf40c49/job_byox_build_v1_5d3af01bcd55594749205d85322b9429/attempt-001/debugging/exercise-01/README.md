# Exercise 01: the wandering jump

The fragment in `BrokenBranchPatch.java.txt` runs after labels have concrete byte
positions. Small straight-line programs pass. An `if` can jump two bytes early,
causing a `VerifyError` or surprising execution.

Identify the mistaken coordinate system, state the JVM rule, and propose a
boundary test covering both a forward and backward branch. Do not merely tweak a
constant until one example works.

