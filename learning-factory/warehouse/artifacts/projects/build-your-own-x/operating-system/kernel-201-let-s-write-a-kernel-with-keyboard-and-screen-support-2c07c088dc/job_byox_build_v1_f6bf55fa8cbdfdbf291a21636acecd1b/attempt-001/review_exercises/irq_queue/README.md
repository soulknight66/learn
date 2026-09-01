# Exercise: shared-count IRQ queue

The author proposes this queue, claiming `volatile` makes it interrupt-safe:

```c
bool push(struct queue *q, struct event event) {
    if (q->count == CAPACITY) return false;
    q->head = (q->head + 1) % CAPACITY;
    q->events[q->head] = event;
    ++q->count;
    return true;
}

bool pop(struct queue *q, struct event *out) {
    if (q->count == 0) return false;
    *out = q->events[q->tail];
    q->tail = (q->tail + 1) % CAPACITY;
    --q->count;
    return true;
}
```

Assume `head`, `tail`, and `count` are volatile, push runs in IRQ context, pop in foreground, and an
interrupt may occur between any foreground instructions.

1. Find the indexing bug independently of concurrency.
2. Give an interleaving that loses a count update.
3. Explain the publication-order requirement.
4. Recommend a bounded design and an explicit overflow policy.
