# Sealed alternatives

`bitmap_frames.c` demonstrates how the frame allocator could store 128 ownership bits in 16 bytes
instead of 128 bytes. It intentionally uses a private type rather than changing the exercise's
public ABI. The lower memory cost trades for masking logic and more involved auditing.

Other plausible variants not implemented here include a buddy allocator for contiguous power-of-two
runs, a free-list allocator with constant-time single-frame operations, a priority scheduler, a
hashed page-map model, and variable-size filesystem storage. Each would change the invariants and
test surface enough to deserve a separate exercise.
