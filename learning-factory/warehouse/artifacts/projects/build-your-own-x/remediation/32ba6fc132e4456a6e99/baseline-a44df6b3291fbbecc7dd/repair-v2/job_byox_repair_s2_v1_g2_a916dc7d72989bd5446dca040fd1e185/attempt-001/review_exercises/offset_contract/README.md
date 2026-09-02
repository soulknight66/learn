# Code review: offsets or end offsets?

Review this proposed high-watermark code for a fixed five-replica partition:

```java
positions.sort(Comparator.reverseOrder());
int quorumIndex = positions.size() / 2 + 1;
long highWatermark = positions.get(quorumIndex);

boolean committed(long recordOffset) {
    return recordOffset <= highWatermark;
}
```

State the contract each value should use, find all indexing/visibility defects,
give one concrete position vector that exposes them, and suggest focused unit
assertions. The sealed review notes are not part of the prompt.
