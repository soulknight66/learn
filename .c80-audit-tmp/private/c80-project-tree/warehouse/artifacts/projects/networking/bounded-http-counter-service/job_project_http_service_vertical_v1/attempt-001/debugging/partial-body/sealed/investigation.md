# Investigation

1. Reproduced with the header plus only five body bytes in the first parser feed.
2. Verified the advertised length and complete combined payload were correct.
3. Compared one-write success with split-write failure, isolating stream reassembly rather than
   JSON semantics or application locking.
4. Asserted that the first feed emits zero requests and the second emits exactly one full body.
5. Ran the same regression against the corrected shared parser.
