# Concepts

- Alignment turns payload addresses and header sizes into invariants, not preferences.
- Alignment is distinct from C effective type. Standard allocated storage can acquire the
  internal metadata type through stores; casting a declared character array cannot.
- Integer-overflow checks must precede rounding and size addition.
- An address-ordered physical list makes adjacent coalescing simple but allocation search
  linear. Best-fit changes selection, not that cost class.
- Segregated free bins accelerate candidate lookup but add a second topology whose membership
  must agree with the physical list through every split, merge, and resize.
- Internal fragmentation is padding/capacity within allocated blocks. External fragmentation
  is free capacity divided among blocks; this pack records `1 - largest_free/free_total`.
- A failed resize must be transactional from the caller's perspective: the old pointer and
  bytes remain valid.
- An invariant checker detects metadata damage early but is not memory-safety hardening.
