# Review answer: VM boundary

The nonzero-intersection test grants a combined READ|WRITE request when the map
has only READ. Requested access must be nonzero, contain no unknown bits, and be
a complete subset: `(mapped & requested) == requested`.

The function dereferences both input and output pointers without validation. It
writes caller-visible output before knowing that access is permitted, violating
failure atomicity. It also performs physical-base-plus-offset before an explicit
overflow check; alignment normally constrains a valid base, but this function's
stated trust boundary does not validate that representation.

Validate table/output pointers, requested bits, and each matching record's
alignment first. Check complete permission inclusion. Compute the offset, prove
`physical_base <= UINT32_MAX - offset`, calculate into a local, and assign the
output only on success. An absent mapping or any failed check leaves output
unchanged.
