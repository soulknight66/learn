# Code-review exercise 01: optimistic frame length

Review this decoder strategy:

> Read the two base bytes. If the length marker is 126 or 127, allocate a string
> of that advertised length, then read the mask and payload into it. Once the
> frame is complete, compare the payload length with `max_frame_bytes` and
> reject it if necessary.

List protocol, memory, and availability problems. Specify the earliest point at
which each length form can be validated. Also consider canonical encodings, the
64-bit high bit, control-frame size, partial input, and whether an invalid frame
may consume bytes belonging to a following frame.

The solution-bearing review is isolated in the evaluator's sealed tree.

