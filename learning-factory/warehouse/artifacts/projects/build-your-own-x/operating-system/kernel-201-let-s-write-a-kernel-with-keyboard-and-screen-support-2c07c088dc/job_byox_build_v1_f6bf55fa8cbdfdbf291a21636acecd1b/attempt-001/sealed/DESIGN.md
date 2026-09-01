# Reference design discussion

This file answers `DESIGN_QUESTIONS.md`; reveal it only after making your own decisions.

1. **Injected surface.** Supplying cells and dimensions removes the physical-address dependency from
   the terminal policy. Tests can use guard cells to detect overrun, tiny dimensions to force wrap
   and scroll, and ordinary memory to inspect exact attributes.
2. **Persistent decoder state.** The `0xe0` prefix survives one call; each left/right modifier
   survives until its own break byte; Caps Lock survives until a later make; and the unsupported
   Pause tail counter survives five calls. Sequences such as `2a 1e aa`, `2a 36 aa 1e`,
   `e0 1d e0 9d`, and `e0 48` isolate those states.
3. **Release ASCII.** Releases carry no ASCII. Translation is an action for text-producing make
   events, not an identity for a physical key. This prevents consumers from treating release as
   duplicate input and avoids ambiguous modifier timing.
4. **Reserved queue slot.** Head belongs to the producer and tail belongs to the consumer. Reserving
   one slot makes equality mean empty and `next(head) == tail` mean full. A shared count would be
   modified by both contexts and would need an atomic read-modify-write or an interrupt critical
   section.
5. **Publication.** The producer writes the event before a release-store of head; the consumer uses
   an acquire-load of head before reading that event. Tail uses the symmetric relation before a slot
   is reused. `volatile` controls compiler treatment of individual accesses but supplies neither
   these cross-object ordering relations nor portable inter-context synchronization.
6. **Overflow.** Dropping newest preserves everything already promised to the consumer. A monotonic
   counter makes the loss visible. Dropping oldest changes a consumer-owned index; silent overwrite
   makes diagnosis especially difficult.
7. **EOI.** Every serviced IRQ must be acknowledged after its device byte is read, whether or not
   decoding emits an event. Otherwise one unknown or prefix byte can leave the PIC's in-service bit
   set and stop subsequent IRQ1 delivery.
8. **Idle race.** An IRQ can enqueue after the empty check but before `hlt`; then the CPU sleeps while
   work is already queued. On one CPU, briefly disabling interrupts around “check then atomically
   `sti; hlt` if empty” closes that window. The sealed production sketch demonstrates the shape.
9. **Paging.** Map VGA physical memory into a deliberate kernel virtual address with device-suitable
   cache attributes, then pass that virtual mapping to the unchanged terminal policy. Mapping and
   lifetime belong outside the terminal module.
10. **Process-facing input.** A kernel input/TTY service should own the IRQ stream, apply line and
    foreground-session policy, buffer bytes or structured events, and expose blocking read/poll
    operations. Processes should not program PIC/PS2 ports or share the raw ISR queue.
