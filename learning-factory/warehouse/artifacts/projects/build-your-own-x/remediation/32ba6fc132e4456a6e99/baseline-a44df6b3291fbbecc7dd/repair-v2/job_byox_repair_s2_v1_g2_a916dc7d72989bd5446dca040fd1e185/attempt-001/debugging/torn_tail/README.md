# Debugging exercise: the disappearing corruption

A candidate recovery loop handles every decoder failure by truncating the file
at the previous valid boundary and continuing startup. During a fault-injection
test, flipping one byte in the middle of the last record makes the broker start
successfully with that record missing.

Identify the violated safety property, explain why “it was in the last segment”
is insufficient evidence of a torn append, and propose the smallest change to
the decoder/recovery contract that retains automatic crash repair. Also name
one test that prevents regression.

Do not inspect evaluator material while solving. The answer is stored only in
this exercise's evaluator-sealed counterpart.
