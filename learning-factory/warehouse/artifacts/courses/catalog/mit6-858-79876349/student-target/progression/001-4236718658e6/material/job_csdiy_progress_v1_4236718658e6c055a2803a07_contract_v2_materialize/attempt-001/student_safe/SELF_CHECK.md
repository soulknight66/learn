# Self-check

Use these questions after completing the task. Record your reasoning in your own submission; this page is not an assessment and contains no solutions.

1. Which facts in this packet come from the normalized source record, and which parts are newly authored practice material?
2. What distinct invariants apply to the data region, role byte, canary, and whole-frame capacity?
3. Why are the 16-byte application boundary and the 24-byte emulator boundary different security concepts?
4. What is the shortest input length that can reach each adjacent region, and how did your tests establish the boundary without special-casing one payload?
5. Can the vulnerable path grant access while its canary remains intact? What does your conclusion imply about relying on a canary as the authorization defense?
6. How does your hardened path demonstrate that rejection occurs before mutation rather than after repair?
7. Which test would reveal accidental frame reuse across requests, and what security property would that reuse threaten?
8. If a result or log contains only lengths, reason codes, and integrity flags, what operational questions can it answer and what sensitive information could still be inferred?
9. Which implementation detail is policy, which is parsing or copying mechanism, and which is diagnostic presentation?
10. What important properties of native memory corruption, web security, and production deployment remain outside this semantic model?
11. What evidence in your report is independently reproducible, and what statements are only your interpretation?
12. What claims would still be unjustified even if every local test passes?
