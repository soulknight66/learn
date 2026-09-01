# Design questions

Write down your answers before opening the starter. Revisit them after your
tests pass.

1. Which object is authoritative when a process state disagrees with the ready
   queue? How can `validate` report the disagreement deterministically?
2. Should calling `schedule` while one process is running keep it running or
   rotate it through the queue? Which requirement decides this?
3. If only one free frame remains and an Sv39 walk needs two intermediate
   tables, what exact state must remain after `map` returns `OutOfFrames`?
4. Why must Sv39 canonicality be tested before extracting VPN indices?
5. Why does `unmap` return a data-frame number but not free that frame?
6. What invariant distinguishes an intermediate PTE from a leaf PTE?
7. Which filesystem path errors can be detected without reading an inode?
8. For `write(file, usize::MAX, &[])`, should an empty write bypass overflow
   checks? State a consistent rule and derive tests from the API contract.
9. What must `remove` validate before it mutates the parent directory?
10. How would the filesystem invariants change if hard links were added?
11. Where would locks be required if scheduler wakeups and filesystem calls
    could occur concurrently? What lock ordering would avoid deadlock?
12. Which properties of this host model transfer to a bootable RISC-V kernel,
    and which are invalidated by hardware, interrupts, or persistence?
