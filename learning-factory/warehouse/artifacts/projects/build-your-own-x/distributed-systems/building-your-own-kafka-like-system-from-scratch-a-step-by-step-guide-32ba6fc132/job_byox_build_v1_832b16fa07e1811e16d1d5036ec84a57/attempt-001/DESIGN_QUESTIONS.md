# Design questions

Answer these after the public tests pass. There is no answer material in this file; justify each
response from the observable contract and from failure scenarios you construct.

1. Which state transitions must be atomic during append, and what would a caller observe if an
   exception occurred halfway through them?
2. Why are `endOffset` and `highWatermark` exclusive? Give the intervals for an empty log and a log
   containing offsets 0 through 3.
3. What distinction does your implementation make between “available” and “in sync”? Describe a
   trace where the distinction matters.
4. What exact facts make a follower eligible to become leader? Is a matching end offset sufficient?
5. Where are defensive copies required? Identify both write-side and read-side aliasing attacks.
6. With three replicas and minimum ISR two, which two-failure sequences reject writes? Which state
   remains readable, and why?
7. What makes recovery idempotent? Consider recovery of an already healthy node and repeated recovery
   of the same failed node.
8. State three representation invariants that, if checked after every mutation, would simplify your
   reasoning.
9. How would the design change if replication were asynchronous and append acknowledgment could occur
   before all available followers copied the record?
10. Which missing mechanism prevents this model from safely handling two isolated leaders in a real
    network partition?
11. If logs were stored on disk, what ordering and durability guarantees would be required before
    returning from append?
12. Propose a state-machine or property-based test generator. Which observations should it compare to
    a simpler model?
