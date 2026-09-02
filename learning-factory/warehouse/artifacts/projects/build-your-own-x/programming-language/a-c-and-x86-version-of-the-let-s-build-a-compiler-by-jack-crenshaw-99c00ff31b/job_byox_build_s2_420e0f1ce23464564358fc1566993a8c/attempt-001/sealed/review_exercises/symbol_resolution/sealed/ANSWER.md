# Answer

The candidate installs the declared name before resolving its initializer, so
`let x = x;` is accepted as a read from an uninitialized slot. Pebble requires
an initializer to see only earlier declarations.

Resolution must first reject a duplicate, then resolve the initializer against
the existing symbol set, then allocate and install the new slot. Capacity must
also be checked before indexing the symbol array. Tests should cover direct
self-reference, a valid reference to an earlier name, duplicates, and the
256/257-variable boundary.
