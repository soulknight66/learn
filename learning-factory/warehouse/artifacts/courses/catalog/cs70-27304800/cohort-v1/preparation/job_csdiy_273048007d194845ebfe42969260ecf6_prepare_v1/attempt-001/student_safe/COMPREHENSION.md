# Comprehension Prompts

**Artifact status:** `PREPARED_NOT_VALIDATED`  
**Unit:** `kickoff_01_stable_matching_engineering`

Answer these prompts in `COMPREHENSION_RESPONSES.md`. Use your own implementation and evidence. A diagram or compact notation is welcome when it makes an argument clearer, but unsupported yes/no answers are not sufficient.

1. **Contract boundary.** State your public operation's preconditions, postconditions, and failure behavior. Pick one malformed input that a mathematically phrased theorem might leave implicit. Trace exactly where your program detects it and why silently accepting it would weaken the meaning of the result.

2. **State and invariant.** Choose three pieces of mutable matching state. For each one, give an invariant that holds before and after every proposal-processing step. Point to the code transition that preserves it.

3. **Termination.** Give a finite progress measure for your implementation. Explain why every iteration changes that measure in one direction and derive a worst-case bound on proposal-processing steps. Account for the empty instance.

4. **Stability.** Assume your program returns a valid bijection. Prove that a blocking pair cannot remain at termination. Your argument must cover both possibilities: the left participant never proposed to that right participant, or did propose and was not ultimately retained.

5. **Proposer-side guarantee.** Explain precisely what left-proposer optimality compares across. Why is it stronger than merely saying that the result is stable? Describe how your claim relates to the order in which currently free left participants are processed.

6. **Cost model.** Separate the costs of validation, rank indexing, the matching phase, and your stability oracle. Give worst-case time and auxiliary-space bounds in terms of (n), and identify the concrete operations on which the bounds depend.

7. **Oracle independence.** Describe a defect in the construction algorithm that could be hidden if the checker reused the algorithm's internal engagement state. Explain how your direct blocking-pair checker avoids sharing that failure mode.

8. **Metamorphic test.** If every participant ID is replaced consistently by a one-to-one renaming while all preference positions remain unchanged, what relationship should hold between the two outputs? State how you tested that relationship and what category of bug it can reveal.

9. **Counterexample work.** Give a smallest instance you can find with more than one stable matching. Enumerate its stable matchings using the blocking-pair definition, then identify the result required when the left side proposes. Show your checks rather than citing a theorem alone.

10. **Changing the model.** Choose exactly one excluded extension—ties, incomplete lists, unacceptable partners, capacities, or concurrent updates. Identify two current contract statements or invariants that no longer suffice, and outline the smallest honest API change you would make before implementing it.

11. **Evidence limits.** Suppose all of your current tests pass. Name one relevant correctness claim they still do not establish by themselves, and state what different kind of evidence supports that claim. Then explain why finishing this kickoff is not evidence of completing the cataloged course.

Do not copy a model solution or examiner material. Cite any optional source you consult and distinguish the source's ideas from your own reasoning.

---

**Provenance:** These unanswered prompts were authored for this kickoff from the supplied CSDIY catalog snapshot at commit `adce8e13789dc16aa6d1fbe163e9541736defae4`. No external course material was retrieved, and no answer key is included here.
