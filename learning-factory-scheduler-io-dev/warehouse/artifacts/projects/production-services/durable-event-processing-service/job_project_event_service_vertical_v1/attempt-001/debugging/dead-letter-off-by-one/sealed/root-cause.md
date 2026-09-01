# Root cause

The poison boundary compared `attempts > max_attempts`. Because attempt count already includes
the active claim, equality is the final permitted attempt and must dead-letter. The off-by-one
adds work and downstream load to every deterministic poison message. Change the comparison to
`>=`; the regression proves buggy failure and reference recovery.
