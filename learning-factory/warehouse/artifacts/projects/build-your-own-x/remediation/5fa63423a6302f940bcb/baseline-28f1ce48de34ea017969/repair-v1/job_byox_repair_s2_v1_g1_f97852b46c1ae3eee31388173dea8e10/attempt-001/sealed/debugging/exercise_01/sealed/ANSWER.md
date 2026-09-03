# Diagnosis

The parent still owns `channel[1]`, a write reference. The consumer's `cat` reads all producer bytes, then blocks because pipe EOF means “no write references exist,” not merely “the producer closed its descriptor.” The parent cannot reach process exit because it is waiting for the blocked consumer, so its write reference stays alive indefinitely.

Immediately after the forks, before local closure, all three processes inherited both descriptors. Each child correctly closes both originals after `dup2`; the producer retains a standard-output reference to the write end, and the consumer retains a standard-input reference to the read end. After the producer exits, the erroneous parent write reference is the sole reason EOF is withheld.

The smallest patch is:

```c
(void)close(channel[0]);
(void)close(channel[1]);
```

Both closures must happen before either wait. A general executor should close a parent's unused write end immediately after each fork, not postpone closure until cleanup.
