# Reference review findings: cross-page copy

High severity: the loop writes the first page before it knows whether later pages exist and are
writable, violating all-or-nothing semantics. Preflight every touched PTE and permission in a first
pass, then copy in a second pass.

High severity: `address + remaining` and page/offset calculations are not shown as overflow-checked;
validate with subtraction against the fixed user-size bound before addition.

Medium severity: a missing PTE should be distinguished from a present read-only PTE according to the
API contract. Null source with nonzero length also needs rejection before any lookup.

Context-dependent: `memcpy` is undefined for overlap. The public VM contract does not grant snapshot
semantics for aliases into physical storage, but using `memmove` avoids same-chunk undefined behavior.

Tests should place writable bytes at the end of page zero and make page one read-only/unmapped, then
prove the original bytes remain. Add exact-end, one-past-end, zero-length, and very large length cases.
