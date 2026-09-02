# Design questions

Write down your answers before implementing each milestone. These are prompts,
not extra requirements.

1. Which bytes does the body checksum cover, and why does the length also need
   an independently verifiable complement?
2. In what order should recovery validate the length pair, bounds, available
   byte count, body checksum, and body metadata?
3. What invariants relate a segment's filename, its first record, the previous
   segment, and an empty final segment?
4. Should a read byte budget count payload bytes, encoded frame bytes, or both?
   What makes the chosen contract deterministic?
5. Why are follower positions end offsets instead of last-record offsets?
6. Can shrinking the in-sync set safely reduce the number of copies needed to
   commit? Construct a failure sequence for your answer.
7. Why must a node advance its term when rejecting a higher-term vote request?
8. Which checks must occur before an append touches disk so a rejected request
   has no partial effect? How will you stop retained log or tracker aliases
   from changing one side of the partition invariant?
9. What should duplicate acknowledgements and duplicate vote requests do?
10. Which additional mechanisms would be necessary before exposing this model
    over an untrusted network in production?
