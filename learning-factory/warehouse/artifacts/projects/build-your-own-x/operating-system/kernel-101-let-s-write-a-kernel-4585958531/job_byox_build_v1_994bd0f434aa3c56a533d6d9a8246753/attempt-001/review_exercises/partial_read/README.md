# Review: partial read

A filesystem read copies `min(file_size, capacity)` bytes and then returns `-1` when capacity is too
small. Review the behavior from both API and caller perspectives. Describe a test that establishes
whether the output buffer changed on failure.
