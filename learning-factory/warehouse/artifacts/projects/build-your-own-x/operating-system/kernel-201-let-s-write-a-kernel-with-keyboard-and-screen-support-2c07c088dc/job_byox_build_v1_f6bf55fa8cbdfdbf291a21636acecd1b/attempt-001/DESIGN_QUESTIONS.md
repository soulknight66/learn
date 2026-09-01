# Design questions

Write down your decisions before looking at sealed discussion material.

1. Why does the terminal accept a cell pointer and dimensions instead of always using `0xb8000` and
   `80x25`? Which mistakes become host-testable?
2. Which decoder state must persist between calls? For each field, identify a byte sequence that
   would expose an incorrect reset.
3. Should a key release carry translated ASCII? Explain how your choice affects clients when Shift
   is released before another key.
4. The queue sacrifices one physical slot. Compare this with adding an explicit count field. Which
   fields would each execution context write?
5. Establish the publication order for a queue push and the observation order for a pop. Why are
   `volatile` indices alone an incomplete portable-C answer?
6. When the queue is full, compare dropping newest, dropping oldest, and overwriting silently. Which
   behavior is easiest to diagnose in a tiny kernel?
7. Where must PIC acknowledgement occur if decoding rejects a byte? What failure follows from
   acknowledging only recognized keys?
8. Identify the race in “check queue; if empty, execute `hlt`.” How could a larger kernel close it?
9. How would paging change the way the VGA buffer is passed to this module?
10. What interface would let multiple processes receive input without exposing scan codes or IRQ
    ownership to each process?
