# Exercise 01 answer

The parent retains `channel[1]`. Even after the producer exits, the kernel sees
a live writer, so the reader cannot observe EOF. The parent must close both
ends after it has forked the consumers:

```c
close(channel[0]);
close(channel[1]);
```

Each child should also close both original descriptors after any required
`dup2`; closing the duplicated source descriptor does not close standard input
or output because they are distinct descriptor-table entries.
