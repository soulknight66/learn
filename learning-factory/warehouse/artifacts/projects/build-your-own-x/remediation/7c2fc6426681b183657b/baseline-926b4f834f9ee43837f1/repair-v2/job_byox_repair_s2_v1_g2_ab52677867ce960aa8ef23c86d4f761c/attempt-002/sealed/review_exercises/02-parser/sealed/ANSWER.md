# Review answer: parser states

A boolean conflates lexical mismatch and numeric overflow, allowing an out-of-range decimal to become
an unknown word or even resolve to a strangely named definition. Return three states: not numeric,
valid numeric, and numeric overflow. Return the cell only with the valid state. Definition-name
validation should reject either numeric state.
