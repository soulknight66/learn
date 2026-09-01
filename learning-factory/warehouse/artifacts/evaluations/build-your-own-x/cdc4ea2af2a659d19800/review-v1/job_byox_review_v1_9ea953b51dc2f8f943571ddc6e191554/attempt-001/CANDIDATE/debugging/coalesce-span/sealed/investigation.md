# Investigation

1. Confirm the reference regression exits zero and the buggy binary exits one.
2. Reduce the history to three allocations and two adjacent frees.
3. Compare the sum of physical header/payload spans before and after the second free.
4. Observe that the list's claimed final address advances by one extra header.
5. Apply `patch.diff`; strict contracts and the deterministic model must still pass.
