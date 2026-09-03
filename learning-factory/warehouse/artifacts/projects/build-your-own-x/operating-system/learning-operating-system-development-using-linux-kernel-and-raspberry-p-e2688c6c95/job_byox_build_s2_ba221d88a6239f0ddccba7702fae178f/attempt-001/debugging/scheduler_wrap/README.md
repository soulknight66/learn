# Debugging case: the disappearing eighth process

A candidate scheduler computes its next slot as follows:

```c
for (step = 1u; step <= MINIOS_MAX_PROCESSES; ++step) {
    size_t index = (start + step) % (MINIOS_MAX_PROCESSES - 1u);
    if (table->slots[index].state == PROC_READY) {
        selected = index;
        break;
    }
}
```

With eight occupied slots, the process stored in slot seven is never selected.
Construct the shortest scheduling trace that exposes the defect, identify the
faulty invariant, and propose a correction that remains safe when `start` is
the last slot.
