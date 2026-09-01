# Diagnosis: jump patch

MNO1 destinations are byte offsets in the serialized code section, not instruction ordinals. Because
`CONST` occupies nine bytes while arithmetic occupies one, ordinals coincide with offsets only in
misleading all-single-byte prefixes. MNO1 operands are also big-endian, while the snippet writes little
endian.

The smallest illustrative prefix is a `CONST`, then a forward `JUMP`, then `HALT`: resolving the HALT
to ordinal 2 writes `02 00 00 00`, which is both the wrong unit and byte order. Use symbolic labels
while constructing records, compute each record's byte offset in a layout pass, then serialize or patch
the big-endian u32 offset. If emitting bytes directly, record `len(code)` at every label and patch with
that value.
