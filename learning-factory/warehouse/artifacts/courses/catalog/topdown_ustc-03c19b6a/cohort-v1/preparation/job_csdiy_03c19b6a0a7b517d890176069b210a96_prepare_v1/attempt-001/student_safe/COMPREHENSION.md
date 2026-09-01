# Comprehension Prompts

Answer each prompt in your own words. Use concrete byte sequences, state transitions, or references to your submitted code/tests where requested. Do not rely on access to the cataloged textbook, videos, slides, or website.

1. A server calls `send` once with a complete response. Explain why a client still cannot treat one receive call as one response. Identify the invariant your reader uses instead.

2. Trace your reader's state and buffers for the fragments `b"HTTP/1.1 200 OK\r\nContent-Len"`, `b"gth: 5\r"`, and `b"\n\r\nA\x00B"`, followed by `b"CD"`. State when each result field becomes trustworthy.

3. Compare these responses: one with no `Content-Length`, one with two equal `Content-Length` fields, and one with two conflicting values. State what your declared contract does for each and why ambiguity is an engineering risk.

4. Distinguish a malformed response, premature EOF, a read timeout, and a body-limit violation. Where does each originate in your design, and what information can safely cross the component boundary?

5. Point to a deterministic test that would fail if the implementation accidentally assumed that `\r\n\r\n` appears within one received fragment. Explain why an ordinary happy-path socket test may miss the defect.

6. Your client records elapsed time and byte counts. Describe one debugging question those events can answer and two conclusions they cannot establish. Discuss one piece of data that should not be logged.

7. Suppose this teaching client were proposed for production use. Name at least five missing protocol, security, operability, or compatibility concerns. Choose one and describe how it would change the current component boundaries or tests.

8. Relate this task to algorithmic reasoning: identify the input-size measures, give the time and auxiliary-space behavior of your head/body accumulation strategy, and explain how the configured caps turn those bounds into an operational guarantee.

---

Provenance: prompts are manager-authored for `kickoff_01_http_over_tcp` from catalog metadata only.  
Validation label: `PREPARED_AWAITING_INDEPENDENT_VALIDATION`.
