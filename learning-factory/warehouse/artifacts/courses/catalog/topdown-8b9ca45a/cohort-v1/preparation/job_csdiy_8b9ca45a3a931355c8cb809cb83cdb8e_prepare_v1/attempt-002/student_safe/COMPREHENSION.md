# Comprehension prompts

Answer in your own words and refer to specific tests or evidence from your implementation. These prompts ask for reasoning; do not answer them with a completion claim.

1. Why can neither a successful TCP connection nor one successful `recv` call establish that a complete HTTP response head has arrived? Name the distinct boundaries involved.

2. Take one valid response from your fixture and divide it so that the end-of-head delimiter spans three socket reads. Describe the parser state after each read and the invariant that remains true.

3. What failure would occur if the parser searched each received fragment independently for the delimiter? Explain how your design avoids that failure while still enforcing the response-head limit.

4. Which parts of header parsing are case-insensitive in your implementation, which bytes are preserved, and what tests make that behavior observable?

5. Compare premature EOF before the response head, timeout while waiting for more bytes, and hitting the size limit. Why should callers be able to tell these outcomes apart?

6. How did you derive multiple fragmentation cases from one canonical response? Explain why this gives stronger evidence than one normal local run, and identify a case it still does not cover.

7. State the time and space complexity of processing a response within your configured limits. Identify any operation in your implementation that could accidentally make repeated fragment processing superlinear.

8. What does your saved application-level byte trace prove? What additional facts could a packet capture show, and what facts would neither artifact prove by itself?

9. If a future unit added chunked transfer decoding, which new parser states, bounds, malformed-input cases, and tests would you introduce? Do not implement that extension in this unit.

10. Name one simplifying assumption in this kickoff that would be unacceptable in a production client. Describe the evidence you would require before removing that assumption safely.
