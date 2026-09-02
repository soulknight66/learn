# VM translation boundary review

Review `candidate.c` against the mapping contract. Assume mappings are aligned
but all public arguments are untrusted.

Identify every case where the function:

- grants an access it should deny;
- changes caller-visible output on failure;
- performs an unsafe or ambiguous address computation.

Describe a validation-and-publication order that resolves the findings. Do not
redesign the mapping representation.
