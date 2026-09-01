<!--
provenance: Manager-authored assessment prompts for this kickoff; no remote course content was retrieved.
validation_label: PREPARED_NOT_VALIDATED
-->

# Comprehension check

Answer each question in `COMPREHENSION_RESPONSES.md`. Use your own implementation, tests, and measurements as evidence. Number answers 1–7, show intermediate states for the trace, and keep each prose answer under 200 words unless a code fragment or table is useful.

1. **Contract boundary.** For each proposed priority—`3`, `3.5`, `True`, `float("nan")`, `float("inf")`, and `"3"`—state whether `push` must accept it. For every rejected value, name the required exception and explain what a caller must observe about the queue afterward.

2. **Invariant and restoration.** State the complete ordering invariant maintained by your representation, including the tie rule. Explain why the invariant puts the correct item at the root and why a successful `push` or `pop` needs repair along only a bounded number of ancestor/descendant links.

3. **Concrete trace.** Ignoring payload labels because all priorities are distinct, start from the valid heap array `[2, 5, 4, 9, 7, 8]`. Show every array state produced when priority `3` is inserted. Then pop the minimum from the resulting heap and show the replacement and every subsequent array state. Identify which comparisons determine each move.

4. **Stable, opaque payloads.** Two distinct payload objects cannot be ordered with `<` and both have priority `7`. Describe how the queue can return them in insertion order without ever comparing the payloads. Name one test that would detect an accidental payload comparison.

5. **Review a defect.** A `pop` implementation always swaps a descending entry with its left child whenever that child is smaller, without comparing the right child. Give a smallest valid pre-pop heap that exposes the defect, trace the faulty result, and state the violated property.

6. **Test evidence.** Explain what the independent reference model contributes beyond hand-picked unit tests. Why must the random seed and operation trace be reproducible, and which observations should be compared after interleaved operations to catch a failure close to its cause?

7. **Performance claim.** Suppose median times rise as workload sizes grow. State what your benchmark can reasonably support, what it cannot prove about worst-case complexity, and two sources of measurement distortion you would consider before drawing a conclusion.

Do not look for or submit copied solution text. If a question reveals a defect in your code, fix the code, preserve an appropriate regression test, and describe that evidence in your response.

---

Preparation provenance: manager-authored for this kickoff from the supplied catalog context; remote content retrieved: no.  
Validation label: **PREPARED_NOT_VALIDATED**.
