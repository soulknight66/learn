# Jump-patching answer

Jump destinations are absolute instruction indexes. `elseStart` already names
the first instruction emitted for the else expression; adding one bypasses its
value push and breaks the join's stack shape. Assign `elseStart` directly to the
false jump. The unconditional jump correctly targets `end`, the first
instruction after the else expression.
