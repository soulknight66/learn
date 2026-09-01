# Sealed alternatives

Alternative valid designs include a ready queue instead of circular scanning, generation-tagged slot
handles instead of monotonic PIDs, a buddy allocator rather than first-free frames, and copy-on-write
replacement rather than in-place block reuse. Each changes observable ordering or capacity and would
need an amended contract and tests.

For hardware, ARMv8-A/AArch64 would use a different exception model and context frame. For filesystem
persistence, a log-structured design avoids in-place metadata ordering but introduces recovery and
garbage collection. These are extensions, not drop-in answers to the fixed ABI.
