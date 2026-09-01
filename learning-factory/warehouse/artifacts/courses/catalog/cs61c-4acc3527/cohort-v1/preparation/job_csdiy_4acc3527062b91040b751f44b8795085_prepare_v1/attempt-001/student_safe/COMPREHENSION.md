# Comprehension Check

> **Artifact label:** Manager-authored learner prompts; awaiting worker-harness validation. This file contains questions, not an answer key.

Write your answers in `COMPREHENSION_RESPONSES.md`. Number them 1–8 and answer in your own words. When asked about implementation behavior, point to a file and function in your submission. Do not answer by quoting tool output without interpreting it.

1. Trace ownership through one successful run: from parser growth, through `int_index_build`, to final cleanup. For each allocation and the file handle, identify who owns it and the event that ends that ownership.

2. Trace two failure runs: one malformed data line after several valid lines, and one index allocation failure. What state must each live object have at the point the program exits, and why must standard output still be empty?

3. State the loop invariant used by your lower-bound implementation. Explain how the invariant gives the required result for an empty index, duplicate values, a key below the minimum, and a key above the maximum.

4. Explain why a subtraction-based sort comparator can be incorrect even when its return type is `int`. Describe the comparison rule your implementation uses across the full `int32_t` domain.

5. Identify every place where your program converts among input text, `intmax_t` (or another parsing type), `int32_t`, `size_t`, and allocation byte counts. For each conversion, state the check that makes it valid.

6. Starting with `src/rankq.c` and `src/int_index.c`, describe preprocessing, compilation, assembly, and linking. What information comes from `include/int_index.h`, what appears in object files, and when is an unresolved function reference connected to its definition?

7. Give one defect that your ordinary tests are well suited to find, one defect a sanitizer run is well suited to find, and one relevant defect neither result proves absent. Tie each claim to a concrete test or limitation in this project.

8. Suppose all of your tests pass. Explain what that result justifies claiming about this unit, what it does not justify claiming about all possible inputs, and why it cannot establish completion of the full architecture course.
