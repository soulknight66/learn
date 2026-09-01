# Bytecode-validation review answer

Indexing before validation permits a negative or oversized operand to panic. Converting `int64` to `int` first can also truncate on narrower architectures, turning an out-of-range value into an apparently unrelated index. Check `operand >= 0` and `operand < int64(SlotCount)` while still in `int64`, after first proving `SlotCount >= 0`; only then convert and index. Short-circuit conditions must not evaluate `initialized[slot]` unless the range check succeeded.
