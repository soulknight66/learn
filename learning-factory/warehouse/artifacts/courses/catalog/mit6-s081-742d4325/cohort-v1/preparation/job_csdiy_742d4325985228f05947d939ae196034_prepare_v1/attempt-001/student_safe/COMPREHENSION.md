# Comprehension Prompts

> Unit: `unit_kickoff_vmwalk_v1`  
> Artifact provenance: course-manager-authored from the supplied catalog snapshot.  
> Validation label: **PROMPTS PREPARED / RESPONSES NOT YET VALIDATED**

Write your responses in `COMPREHENSION_RESPONSES.md` at the submission root. Answer each prompt in at most 120 words. Refer to a test or a specific source location when the prompt asks for one. Submit only your own explanations.

1. Choose one successful, nontrivial access from your tests. Identify its two indices, offset, selected physical page number, and resulting physical address. Cite the test case.

2. Why does a valid access that reports a modeled fault still lead to process exit status `0`, while malformed trace input leads to status `2`?

3. Identify one mapping or parsing invariant, where your implementation enforces it, and an observable defect that could occur if that enforcement were removed.

4. Which two tests distinguish an absent mapping from a present mapping that lacks the requested permission? What plausible implementation mistake would those tests expose?

5. Describe how two different virtual pages can refer to the same physical page in this model. Explain the role of each address's offset in the resulting physical addresses.

6. Identify one numeric or line-reading operation that could truncate or overflow data. Explain the defense implemented in your program and cite its location.

7. Select one real operating-system feature deliberately excluded from this unit. How would adding it change the program's state, interface, or tests?

8. Suppose `evidence/test.log` reports success, but a controlled clean rerun fails. Which observation should govern the unit's validation state, and why?
