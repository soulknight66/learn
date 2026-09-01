# Precedence debugging answer

The algorithm's comparison is appropriate for left-associative operators, but the table reverses the
two precedence tiers. With the supplied table, `+` remains above `*`, producing `1 2 + 3 *` for the
smallest failing input.

Assign additive operators a lower numeric precedence than multiplicative operators. Keep `+` and `-`
equal, and keep `*` and `/` equal, so the existing greater-than-or-equal pop condition preserves left
associativity within each tier. The corrected file is `fixed-parser.js`.
