# Comprehension Check

Course ID: `course_23fa038d619a5b3482e8c8eadb3e2d78`  
Unit ID: `kickoff_01_lexical_contracts`  
Validation label: `LEARNER_SAFE_QUESTIONS_PENDING_HARNESS_VALIDATION`  
Provenance: manager-authored for this kickoff from the supplied catalog topic scope; no external answers or course materials were retrieved.

Answer all questions in `responses/COMPREHENSION_RESPONSES.md`. Use your own reasoning. Where a question asks about implementation evidence, cite a file, function/type, or test in your submission. Do not paste program output without explaining it.

1. What separate meanings do token kind, lexeme, and starting position carry? Give one concrete downstream use for each, and explain why collapsing any two would weaken the library contract.

2. For the one-line input below, list every token through `EOF` as `(position, kind, lexeme)` and explain the two precedence decisions involved.

   ```text
   int ifx=if==0;
   ```

3. For this two-line input, list every emitted token and its starting position. Then identify the scanner state or invariant that prevents characters inside the comment from becoming tokens.

   ```text
   a/* x
   y */==b
   ```

4. Consider `ifelse != !`. What is the observable CLI result under the atomic-output rule? Identify the position and diagnostic code, and explain what happens to otherwise valid tokens that precede the error.

5. Trace line and column changes for the byte sequence `a<TAB>b<CR><LF>c`, where the angle-bracketed names denote the corresponding bytes. Which focused automated test in your suite protects that behavior from regression?

6. Why does this task require the CLI to finish scanning before printing tokens? Describe one benefit, one cost, and a different API you would offer if a future client needed true streaming.

7. Suppose a mutation changes fixed-token matching to accept the shortest operator first. Give the smallest useful set of inputs that exposes the defect, state the observations your tests would compare, and cite the test that kills it.

8. A future version proposes nested block comments. Without implementing them, describe the smallest state change needed, the new invariant at end of input, and three boundary tests that would distinguish nesting from the current contract.

9. If the hand-written scanner were later replaced with a generated Flex scanner, which observable behaviors must remain compatible for callers? Identify one behavior that is easy to lose during that replacement and the test evidence that would catch it.

10. State the strongest claim your current evidence supports, one important behavior it does not establish, and the next test or review action that would reduce the highest remaining risk. Keep the claim bounded to this kickoff.
