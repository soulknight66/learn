# Comprehension Check

Answer these questions in `COMPREHENSION_RESPONSES.md` after completing the implementation and tests. Use your own design and observed evidence. There is no answer key in the learner packet.

1. State the cache's abstract state and at least four representation invariants. For each invariant, name the operations that can threaten it.

2. Give a linearization point for `get`, absent-key `insert`, existing-key `insert`, and `remove` in your implementation. Explain why each point lies between invocation and response and yields a legal sequential history.

3. A capacity-one cache starts empty. Thread A calls `insert("a", 1)` while thread B calls `insert("b", 2)`, and the calls overlap. Enumerate the permitted pairs of outcomes and final states. Name at least two impossible observations and connect each to the contract.

4. A capacity-two cache executes, without overlap: insert `a`, insert `b`, update `a`, then insert `c`. Which key must the fourth operation evict? Explain which part of the contract determines the result and what bug would produce the other answer.

5. Why does adding a short sleep to a thread test fail to establish an interleaving? Explain how your barrier-start tests avoid schedule-specific expected values while still detecting useful failures.

6. Describe what mutex poisoning signals, how your public API reports it, and one reasonable alternative policy. What tradeoff would the alternative introduce?

7. Suppose the cache were changed from one mutex to shards or to a lock-free representation. Identify three parts of your correctness argument or test strategy that would need to be reconsidered. Do not design the replacement implementation.

8. Separate the claims supported by a passing test run, the claims supported by your design argument, and the claims not established by this kickoff. Why would even a perfect submission not establish completion of the cataloged course?
