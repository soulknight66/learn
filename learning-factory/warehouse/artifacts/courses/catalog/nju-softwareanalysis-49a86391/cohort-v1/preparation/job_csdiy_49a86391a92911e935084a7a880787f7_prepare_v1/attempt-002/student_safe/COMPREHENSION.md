# Comprehension Prompts

Answer each prompt in `COMPREHENSION_RESPONSES.md`. Use your own implementation as evidence where requested. These are questions only; no answer key is included.

1. Static analysis reasons about a program without running that program. What useful information is discarded when `cfgcheck` treats ordinary instruction and condition text as opaque? Why can its reachability result still be meaningful?

2. For this project, distinguish the input text, the validated IR model, and the CFG. Name one invariant that belongs at each layer and explain why placing all three in one data structure would make defects harder to isolate.

3. A branch is allowed to name the same block as both its true and false target. Explain how your model represents that terminator while keeping graph adjacency duplicate-free. Point to the tests that establish the behavior.

4. Why does the specification reject an unknown jump target instead of silently creating a block? Describe one downstream analysis error that silent repair could cause.

5. State the traversal invariant used by your reachability implementation. Explain why the algorithm terminates on a self-loop and give its time and auxiliary-space complexity in terms of vertices and edges.

6. Identify every source of potentially unstable iteration order in your implementation. How do you make output byte-for-byte reproducible without accidentally changing branch semantics?

7. Choose one malformed-input test. Explain the defect it localizes, the observable contract it checks, and a plausible incorrect implementation that the test would catch.

8. Suppose a later unit adds backward liveness analysis. What additional facts would each block need, in which direction would information flow, and why would a fixed-point computation be needed on cyclic CFGs? Keep this conceptual; do not implement the extension.

9. Describe one change you made, or would make, after reviewing the separation between library code and the command-line adapter. Connect it to testability or error handling rather than personal style.

---

Provenance: learner-safe, manager-authored comprehension prompts for kickoff unit `unit_kickoff_ir_cfg_reachability_v1`. No answers, grading weights, or examiner-only criteria are included.
