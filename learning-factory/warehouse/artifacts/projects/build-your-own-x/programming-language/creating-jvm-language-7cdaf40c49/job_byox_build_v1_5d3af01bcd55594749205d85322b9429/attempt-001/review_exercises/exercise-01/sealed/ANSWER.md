# Exercise 01 sealed review

High-severity findings:

- Constant-pool index zero is reserved, and the serialized count must be the
  number of slots plus one. Returning zero makes the first reference invalid.
- A `HashMap` iteration order is not the assigned index order and is not a
  deterministic serialization contract. Assign indexes in an insertion-ordered
  table and serialize an indexed list.
- Class-file entries require tag-specific binary encodings. `writeUTF` alone is
  not a valid constant-pool entry, and `toString()` is not a semantic encoding.
- The `u2` count and index space need a pre-insertion bound check. Large inputs
  otherwise wrap during serialization.
- Real long/double entries consume two slots (not used by current Sprig, but the
  abstraction claims generic values and would be unsafe when extended).
- `entries.size()` inside `putIfAbsent` couples assigned values to map membership
  and cannot represent dependency-first construction such as UTF-8 before Class.
- I/O exceptions are infrastructure errors; capacity errors caused by source
  should become stable `E_LIMIT` diagnostics before any partial artifact escapes.

Tests should parse indexes from emitted bytes rather than compare only file size,
repeat emission in fresh processes, exercise deduplication and dependency order,
and generate the exact maximum plus one entry.

