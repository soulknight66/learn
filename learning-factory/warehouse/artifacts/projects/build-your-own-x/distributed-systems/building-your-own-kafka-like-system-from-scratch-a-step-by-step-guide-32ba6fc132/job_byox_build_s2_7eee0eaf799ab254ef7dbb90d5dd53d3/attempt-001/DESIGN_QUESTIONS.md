# Design questions

Write down your answers before implementing each milestone. These are prompts,
not extra requirements.

1. Which bytes does the checksum cover, and what failure becomes ambiguous if
   the length prefix is excluded?
2. How can recovery tell a torn append from corruption without trusting an
   absurd or negative length field?
3. What invariants relate a segment's filename, its first record, the previous
   segment, and an empty final segment?
4. Should a read byte budget count payload bytes, encoded frame bytes, or both?
   What makes the chosen contract deterministic?
5. Why are follower positions end offsets instead of last-record offsets?
6. Can shrinking the in-sync set safely reduce the number of copies needed to
   commit? Construct a failure sequence for your answer.
7. Why must a node advance its term when rejecting a higher-term vote request?
8. Which checks must occur before an append touches disk so a rejected request
   has no partial effect?
9. What should duplicate acknowledgements and duplicate vote requests do?
10. Which additional mechanisms would be necessary before exposing this model
    over an untrusted network in production?
